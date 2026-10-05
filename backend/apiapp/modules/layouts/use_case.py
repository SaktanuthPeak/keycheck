"""Layout service (Spec §11.1, §12.1): seed public layouts from layouts/*.json, serve the contract Layout shape."""

import json
from pathlib import Path

from fastapi import Request
from loguru import logger

from .model import LayoutRecord
from .repository import LayoutRepo
from .schemas import LayoutListResponse, LayoutResponse, LayoutSlot, ReferencePoint


def parse_layout_file(path: Path) -> LayoutRecord:
    d = json.loads(path.read_text(encoding="utf-8"))
    ref = d["reference_points_definition"]
    slot_ids = {s["slot_id"] for s in d["slots"]}
    if len(ref["order"]) != 4 or not set(ref["slot_ids"]) <= slot_ids:
        raise ValueError("bad reference_points_definition")
    return LayoutRecord(layout_id=d["layout_id"], version=int(d["version"]), name=d.get("name", d["layout_id"]),
                        supported_form_factors=list(d.get("supported_form_factors", [])),
                        internal_only=bool(d.get("internal_only", False)), definition=d)


class LayoutService:
    def __init__(self, layouts: LayoutRepo) -> None:
        self.layouts = layouts

    async def seed(self, layouts_dir: Path) -> int:
        """Top-level *.json only (layouts/eval/ holds internal evaluation layouts); internal_only ones are skipped."""
        n = 0
        for p in sorted(Path(layouts_dir).glob("*.json")):
            try:
                rec = parse_layout_file(p)
            except Exception as e:
                logger.warning("skip layout file {}: {}", p.name, type(e).__name__)
                continue
            if rec.internal_only:
                continue
            await self.layouts.upsert(rec)
            n += 1
        logger.info("layouts seeded: {}", n)
        return n

    async def get_public(self, layout_id: str) -> LayoutRecord | None:
        rec = await self.layouts.latest(layout_id)
        return None if rec is None or rec.internal_only else rec

    async def list_public(self) -> LayoutListResponse:
        recs = [r for r in await self.layouts.list_latest() if not r.internal_only]
        return LayoutListResponse(layouts=[self.to_response(r) for r in recs])

    @staticmethod
    def to_response(rec: LayoutRecord) -> LayoutResponse:
        d = rec.definition
        by_id = {s["slot_id"]: s for s in d["slots"]}
        ref = d["reference_points_definition"]
        return LayoutResponse(
            layout_id=rec.layout_id,
            version=rec.version,
            name=rec.name,
            supported_form_factors=rec.supported_form_factors,
            reference_points=[
                ReferencePoint(order=o, slot_id=sid, expected_label=by_id[sid]["expected_label"])
                for o, sid in zip(ref["order"], ref["slot_ids"], strict=True)
            ],
            slots=[LayoutSlot(slot_id=s["slot_id"], row=s["row"], col=s["col"], expected_label=s["expected_label"])
                   for s in d["slots"]],
        )


def get_layout_service(request: Request) -> LayoutService:
    return request.app.state.container.layout_service
