"""Inference wrappers returning (boxes_px xyxy, scores) per canvas. Low score floor; thresholds are applied later."""
from __future__ import annotations

import numpy as np


class YoloDetector:
    def __init__(self, weights: str, imgsz: int = 640, device: str | None = None, max_det: int = 300, conf_floor: float = 0.05, iou: float = 0.6):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.kw = dict(imgsz=imgsz, device=device, max_det=max_det, conf=conf_floor, iou=iou, verbose=False)

    def predict(self, canvases: list[np.ndarray], batch: int = 16):
        out = []
        for i in range(0, len(canvases), batch):
            for r in self.model.predict(canvases[i:i + batch], **self.kw):
                out.append((r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()))
        return out


def build_frcnn(min_size: int, max_size: int, max_det: int, score_thresh: float, nms_thresh: float, pretrained: bool):
    import torchvision
    from torchvision.models.detection import FasterRCNN_ResNet50_FPN_V2_Weights, fasterrcnn_resnet50_fpn_v2
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    m = fasterrcnn_resnet50_fpn_v2(weights=FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1 if pretrained else None, weights_backbone=None,
                                   min_size=min_size, max_size=max_size, box_detections_per_img=max_det,
                                   box_score_thresh=score_thresh, box_nms_thresh=nms_thresh)
    m.roi_heads.box_predictor = FastRCNNPredictor(m.roi_heads.box_predictor.cls_score.in_features, 2)
    return m


class FrcnnDetector:
    def __init__(self, checkpoint: str, model_cfg: dict, device: str | None = None):
        import torch
        self.torch = torch
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = build_frcnn(model_cfg["min_size"], model_cfg["max_size"], model_cfg["box_detections_per_img"],
                                 model_cfg["box_score_thresh"], model_cfg["box_nms_thresh"], pretrained=False)
        ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
        self.model.load_state_dict(ck["model"] if "model" in ck else ck)
        self.model.to(self.device).eval()

    def predict(self, canvases: list[np.ndarray], batch: int = 8):
        torch = self.torch
        out = []
        with torch.no_grad():
            for i in range(0, len(canvases), batch):
                ims = [torch.from_numpy(c[:, :, ::-1].copy()).permute(2, 0, 1).float().div(255).to(self.device) for c in canvases[i:i + batch]]
                for r in self.model(ims):
                    out.append((r["boxes"].cpu().numpy(), r["scores"].cpu().numpy()))
        return out
