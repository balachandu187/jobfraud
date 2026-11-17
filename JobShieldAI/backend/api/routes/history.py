"""
History endpoints.

    GET    /api/history              list scans (filter + search + pagination)
    GET    /api/history/stats        tier counts
    GET    /api/history/{scan_id}    one scan in full
    DELETE /api/history/{scan_id}    delete one scan
    DELETE /api/history              purge everything
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas.history_schema import DeleteResponse, HistoryStats, ScanSummary
from backend.database import crud
from backend.database.connection import get_db

router = APIRouter(prefix="/api/history", tags=["history"])

VALID_LEVELS = {"Low Risk", "Medium Risk", "High Risk"}


@router.get("", response_model=List[ScanSummary], summary="List analysed advertisements")
def list_history(
    limit: int = Query(100, ge=1, le=500, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Rows to skip, for pagination"),
    risk_level: Optional[str] = Query(None, description="Low Risk | Medium Risk | High Risk"),
    search: Optional[str] = Query(None, description="Free-text match on title, company or text"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Newest first. Filtering and search happen in SQL, not in the browser."""
    if risk_level and risk_level not in VALID_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"risk_level must be one of {sorted(VALID_LEVELS)}",
        )
    scans = crud.list_scans(
        db, limit=limit, offset=offset, risk_level=risk_level, search=search
    )
    return [scan.to_history_dict() for scan in scans]


@router.get("/stats", response_model=HistoryStats, summary="Aggregate history counts")
def history_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Totals per risk tier plus the average score, computed in SQL."""
    stats = crud.statistics(db)
    return {
        "total_scans": stats["total_scans"],
        "low_risk_count": stats["low_risk_count"],
        "medium_risk_count": stats["medium_risk_count"],
        "high_risk_count": stats["high_risk_count"],
        "average_risk_score": stats["average_risk_score"],
        "genuine_count": stats["genuine_count"],
        "suspicious_count": stats["suspicious_count"],
    }


# NOTE: /stats is declared before /{scan_id} so the literal path wins routing.
@router.get("/{scan_id}", response_model=ScanSummary, summary="Full detail of one scan")
def get_history_item(scan_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    scan = crud.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return scan.to_history_dict()


@router.delete("/{scan_id}", response_model=DeleteResponse, summary="Delete one scan")
def delete_history_item(scan_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not crud.delete_scan(db, scan_id):
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return {"success": True, "deleted_id": scan_id, "message": f"Scan {scan_id} deleted"}


@router.delete("", response_model=DeleteResponse, summary="Delete all scans")
def delete_all_history(db: Session = Depends(get_db)) -> Dict[str, Any]:
    deleted = crud.delete_all_scans(db)
    return {"success": True, "message": f"Deleted {deleted} scan record(s)"}
