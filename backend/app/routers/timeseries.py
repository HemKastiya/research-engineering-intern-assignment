import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
from fastapi import APIRouter, Depends
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from core.mongo import get_db
from ml.summarizer import summarize_trend

router = APIRouter()


WEEKDAY_LABELS = {
    1: "Sunday",
    2: "Monday",
    3: "Tuesday",
    4: "Wednesday",
    5: "Thursday",
    6: "Friday",
    7: "Saturday",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_match(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict[str, Any]:
    match: dict[str, Any] = {}

    if subreddit:
        match["subreddit"] = subreddit
    if query:
        match["$text"] = {"$search": query}
    if from_date or to_date:
        match["created_date"] = {}
        if from_date:
            match["created_date"]["$gte"] = from_date
        if to_date:
            match["created_date"]["$lte"] = to_date

    return match


async def _fetch_daily_timeseries(db, match: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.extend(
        [
            {
                "$group": {
                    "_id": "$created_date",
                    "count": {"$sum": 1},
                    "avg_score": {"$avg": "$score"},
                    "avg_engagement": {"$avg": "$engagement"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    )

    cursor = db.posts.aggregate(pipeline)
    results = await cursor.to_list(length=None)

    return [
        {
            "date": str(r.get("_id", "")),
            "count": int(r.get("count", 0)),
            "avg_score": _safe_float(r.get("avg_score", 0.0)),
            "avg_engagement": _safe_float(r.get("avg_engagement", 0.0)),
        }
        for r in results
        if r.get("_id")
    ]


async def _fetch_subreddit_distribution(db, match: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.extend(
        [
            {"$group": {"_id": {"$ifNull": ["$subreddit", "unknown"]}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
    )

    cursor = db.posts.aggregate(pipeline)
    rows = await cursor.to_list(length=limit)
    return [{"label": str(row.get("_id", "unknown")), "value": int(row.get("count", 0))} for row in rows]


async def _fetch_weekday_distribution(db, match: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.extend(
        [
            {
                "$addFields": {
                    "_created_utc_num": {
                        "$convert": {
                            "input": "$created_utc",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "_created_date_ts": {
                        "$toDate": {"$multiply": ["$_created_utc_num", 1000]}
                    }
                }
            },
            {"$group": {"_id": {"$dayOfWeek": "$_created_date_ts"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
    )

    cursor = db.posts.aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    return [
        {
            "label": WEEKDAY_LABELS.get(int(row.get("_id", 0)), f"Day {row.get('_id')}"),
            "value": int(row.get("count", 0)),
        }
        for row in rows
    ]


async def _fetch_score_buckets(db, match: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.extend(
        [
            {
                "$bucket": {
                    "groupBy": "$score",
                    "boundaries": [-1000000, 0, 5, 20, 50, 100, 1000, 1000000],
                    "default": "1000+",
                    "output": {"count": {"$sum": 1}},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    )

    bucket_labels = {
        -1000000: "< 0",
        0: "0-4",
        5: "5-19",
        20: "20-49",
        50: "50-99",
        100: "100-999",
        1000: "1000+",
    }

    cursor = db.posts.aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    formatted: list[dict[str, Any]] = []
    for row in rows:
        bucket_id = row.get("_id")
        if isinstance(bucket_id, (int, float)):
            label = bucket_labels.get(int(bucket_id), str(bucket_id))
        else:
            label = str(bucket_id)

        formatted.append({"label": label, "value": int(row.get("count", 0))})

    return formatted


async def _fetch_analytics_facets(
    db,
    match: dict[str, Any],
    subreddit_limit: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.append(
        {
            "$facet": {
                "daily_timeseries": [
                    {
                        "$group": {
                            "_id": "$created_date",
                            "count": {"$sum": 1},
                            "avg_score": {"$avg": "$score"},
                            "avg_engagement": {"$avg": "$engagement"},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],
                "subreddit_distribution": [
                    {"$group": {"_id": {"$ifNull": ["$subreddit", "unknown"]}, "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": subreddit_limit},
                ],
                "weekday_distribution": [
                    {
                        "$addFields": {
                            "_created_utc_num": {
                                "$convert": {
                                    "input": "$created_utc",
                                    "to": "double",
                                    "onError": 0,
                                    "onNull": 0,
                                }
                            }
                        }
                    },
                    {
                        "$addFields": {
                            "_created_date_ts": {"$toDate": {"$multiply": ["$_created_utc_num", 1000]}}
                        }
                    },
                    {"$group": {"_id": {"$dayOfWeek": "$_created_date_ts"}, "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "score_buckets": [
                    {
                        "$bucket": {
                            "groupBy": "$score",
                            "boundaries": [-1000000, 0, 5, 20, 50, 100, 1000, 1000000],
                            "default": "1000+",
                            "output": {"count": {"$sum": 1}},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],
            }
        }
    )

    cursor = db.posts.aggregate(pipeline, allowDiskUse=True)
    facet_rows = await cursor.to_list(length=1)
    if not facet_rows:
        return [], [], [], []

    facet = facet_rows[0]
    raw_timeseries = facet.get("daily_timeseries", [])
    raw_subreddits = facet.get("subreddit_distribution", [])
    raw_weekdays = facet.get("weekday_distribution", [])
    raw_buckets = facet.get("score_buckets", [])

    time_series = [
        {
            "date": str(r.get("_id", "")),
            "count": int(r.get("count", 0)),
            "avg_score": _safe_float(r.get("avg_score", 0.0)),
            "avg_engagement": _safe_float(r.get("avg_engagement", 0.0)),
        }
        for r in raw_timeseries
        if r.get("_id")
    ]

    subreddit_distribution = [
        {"label": str(row.get("_id", "unknown")), "value": int(row.get("count", 0))}
        for row in raw_subreddits
    ]

    weekday_distribution = [
        {
            "label": WEEKDAY_LABELS.get(int(row.get("_id", 0)), f"Day {row.get('_id')}"),
            "value": int(row.get("count", 0)),
        }
        for row in raw_weekdays
    ]

    bucket_labels = {
        -1000000: "< 0",
        0: "0-4",
        5: "5-19",
        20: "20-49",
        50: "50-99",
        100: "100-999",
        1000: "1000+",
    }
    score_buckets: list[dict[str, Any]] = []
    for row in raw_buckets:
        bucket_id = row.get("_id")
        if isinstance(bucket_id, (int, float)):
            label = bucket_labels.get(int(bucket_id), str(bucket_id))
        else:
            label = str(bucket_id)
        score_buckets.append({"label": label, "value": int(row.get("count", 0))})

    return time_series, subreddit_distribution, weekday_distribution, score_buckets


def _parse_date_or_none(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except Exception:
        return None


def _compute_ml_models(time_series: list[dict[str, Any]]) -> dict[str, Any]:
    if not time_series:
        return {
            "trend_regression": {
                "slope": 0.0,
                "r2": 0.0,
                "direction": "flat",
                "trend_line": [],
                "projected_next": [],
            },
            "anomalies": [],
            "daily_clusters": {"n_clusters": 0, "clusters": [], "assignments": []},
        }

    counts = np.array([_safe_float(point.get("count", 0.0)) for point in time_series], dtype=float)
    avg_scores = np.array([_safe_float(point.get("avg_score", 0.0)) for point in time_series], dtype=float)
    avg_engagements = np.array([_safe_float(point.get("avg_engagement", 0.0)) for point in time_series], dtype=float)
    x = np.arange(len(time_series), dtype=float).reshape(-1, 1)

    model = LinearRegression()
    model.fit(x, counts)
    trend_pred = model.predict(x)

    slope = _safe_float(model.coef_[0], 0.0)
    r2 = _safe_float(r2_score(counts, trend_pred), 0.0) if len(counts) > 1 else 0.0

    if slope > 0.05:
        direction = "upward"
    elif slope < -0.05:
        direction = "downward"
    else:
        direction = "flat"

    parsed_dates = [_parse_date_or_none(point.get("date", "")) for point in time_series]
    fallback_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    last_date = next((date for date in reversed(parsed_dates) if date is not None), fallback_start)

    projected_next: list[dict[str, Any]] = []
    future_x = np.arange(len(time_series), len(time_series) + 7, dtype=float).reshape(-1, 1)
    future_preds = model.predict(future_x)
    for offset, pred in enumerate(future_preds, start=1):
        projected_next.append(
            {
                "date": (last_date + timedelta(days=offset)).strftime("%Y-%m-%d"),
                "predicted_count": max(0, int(round(_safe_float(pred, 0.0)))),
            }
        )

    trend_line = [
        {
            "date": point.get("date"),
            "predicted_count": max(0, int(round(_safe_float(pred, 0.0)))),
        }
        for point, pred in zip(time_series, trend_pred)
    ]

    feature_matrix = np.column_stack([counts, avg_scores, avg_engagements])

    anomalies: list[dict[str, Any]] = []
    if len(time_series) >= 10:
        contamination = min(0.18, max(0.05, 3.0 / len(time_series)))
        anomaly_model = IsolationForest(random_state=42, contamination=contamination)
        anomaly_labels = anomaly_model.fit_predict(feature_matrix)

        for idx, label in enumerate(anomaly_labels):
            if label == -1:
                anomalies.append(
                    {
                        "date": time_series[idx].get("date"),
                        "count": int(counts[idx]),
                        "avg_score": _safe_float(avg_scores[idx]),
                        "avg_engagement": _safe_float(avg_engagements[idx]),
                    }
                )

    cluster_payload = {"n_clusters": 0, "clusters": [], "assignments": []}
    if len(time_series) >= 6:
        n_clusters = min(4, max(2, len(time_series) // 25 + 2))
        scaler = StandardScaler()
        scaled = scaler.fit_transform(feature_matrix)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(scaled)

        assignments = []
        for idx, label in enumerate(labels):
            assignments.append(
                {
                    "date": time_series[idx].get("date"),
                    "cluster_id": int(label),
                    "count": int(counts[idx]),
                    "avg_score": _safe_float(avg_scores[idx]),
                    "avg_engagement": _safe_float(avg_engagements[idx]),
                }
            )

        clusters = []
        for cluster_id in sorted(set(labels)):
            cluster_points = feature_matrix[labels == cluster_id]
            clusters.append(
                {
                    "cluster_id": int(cluster_id),
                    "days": int(cluster_points.shape[0]),
                    "avg_count": _safe_float(cluster_points[:, 0].mean()),
                    "avg_score": _safe_float(cluster_points[:, 1].mean()),
                    "avg_engagement": _safe_float(cluster_points[:, 2].mean()),
                }
            )

        cluster_payload = {
            "n_clusters": int(n_clusters),
            "clusters": clusters,
            "assignments": assignments,
        }

    return {
        "trend_regression": {
            "slope": slope,
            "r2": r2,
            "direction": direction,
            "trend_line": trend_line,
            "projected_next": projected_next,
        },
        "anomalies": anomalies,
        "daily_clusters": cluster_payload,
    }


@router.get("/")
async def get_timeseries(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db=Depends(get_db),
):
    match = _build_match(query=query, subreddit=subreddit, from_date=from_date, to_date=to_date)
    return await _fetch_daily_timeseries(db, match)


@router.get("/analytics")
async def get_timeseries_analytics(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db=Depends(get_db),
):
    match = _build_match(query=query, subreddit=subreddit, from_date=from_date, to_date=to_date)

    (
        time_series,
        subreddit_distribution,
        weekday_distribution,
        score_buckets,
    ) = await _fetch_analytics_facets(
        db,
        match,
        subreddit_limit=10,
    )

    ml_models = await asyncio.to_thread(_compute_ml_models, time_series)

    return {
        "time_series": time_series,
        "subreddit_distribution": subreddit_distribution,
        "weekday_distribution": weekday_distribution,
        "score_buckets": score_buckets,
        "ml_models": ml_models,
    }


@router.get("/topics")
async def get_timeseries_topics():
    # Placeholder: implementation requires mapping cluster arrays back over time.
    return []


@router.get("/summary")
async def get_timeseries_summary(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db=Depends(get_db),
):
    data = await get_timeseries(query, subreddit, from_date, to_date, db)
    summary = summarize_trend(data, query or subreddit or "all topics")
    return {"summary": summary}
