#!/usr/bin/env python3
"""Restore a verified real-photo region while preserving all unmasked RGB pixels."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def rgb(path):
    with Image.open(path) as im:
        if "A" in im.getbands() or "transparency" in im.info:
            raise ValueError("Transparent inputs are not supported; supply opaque photographs")
        return np.array(ImageOps.exif_transpose(im).convert("RGB"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def point_array(value, shape, label):
    points = np.asarray(value, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 4:
        raise ValueError(label + " must contain at least four [x,y] pairs")
    if not np.isfinite(points).all():
        raise ValueError(label + " must be finite")
    if np.linalg.matrix_rank(points - points.mean(axis=0)) < 2:
        raise ValueError(label + " are collinear")
    if len(np.unique(points, axis=0)) != len(points):
        raise ValueError(label + " contain duplicate points")
    height, width = shape[:2]
    if (points < 0).any() or (points[:, 0] >= width).any() or (points[:, 1] >= height).any():
        raise ValueError(label + " are outside the displayed image coordinates")
    return points


def repair(source_path, target_path, mask_path, output_path, *, points_path=None,
           aligned=False, feather=0.0, max_error=2.0):
    output = Path(output_path)
    receipt = output.with_suffix(output.suffix + ".json")
    if output.suffix.lower() != ".png":
        raise ValueError("Output must be PNG to preserve unmasked pixels")
    if output.exists() or receipt.exists():
        raise FileExistsError("Output or receipt already exists; choose a new version")
    if bool(aligned) == bool(points_path):
        raise ValueError("Choose exactly one of --aligned or --points")
    if not np.isfinite(feather) or feather < 0 or not np.isfinite(max_error) or max_error <= 0:
        raise ValueError("Feather must be nonnegative; max-error must be positive")
    source, target = rgb(source_path), rgb(target_path)
    with Image.open(mask_path) as im:
        if "A" in im.getbands() or "transparency" in im.info:
            raise ValueError("Use an opaque grayscale mask, not an alpha image")
        mask = np.array(ImageOps.exif_transpose(im).convert("L"))
    if mask.shape != target.shape[:2] or not np.any(mask):
        raise ValueError("Mask must match target dimensions and contain a nonzero region")
    support = mask > 0
    matrix, residual = np.eye(3), 0.0
    if aligned:
        if source.shape != target.shape:
            raise ValueError("Aligned source and target must have identical dimensions")
        warped = source
    else:
        config = json.loads(Path(points_path).read_text(encoding="utf-8"))
        src = point_array(config["source_points"], source.shape, "source_points")
        dst = point_array(config["target_points"], target.shape, "target_points")
        if src.shape != dst.shape:
            raise ValueError("Point arrays must have the same length")
        matrix, _ = cv2.findHomography(src, dst, method=0)
        if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
            raise ValueError("No reliable homography; check control points")
        projected = cv2.perspectiveTransform(src.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        residual = float(np.linalg.norm(projected - dst, axis=1).max())
        if not np.isfinite(residual) or residual > max_error:
            raise ValueError("Control point reprojection error exceeds max-error")
        height, width = target.shape[:2]
        warped = cv2.warpPerspective(source, matrix, (width, height), flags=cv2.INTER_LINEAR)
        coverage = cv2.warpPerspective(np.full(source.shape[:2], 255, np.uint8),
                                       matrix, (width, height), flags=cv2.INTER_LINEAR)
        if np.any(coverage[support] != 255):
            raise ValueError("Repair mask includes area without valid source coverage")
    alpha = mask.astype(np.float64) / 255.0
    if feather:
        # Padding ensures even a full-frame mask has a well-defined inside edge.
        distance = cv2.distanceTransform(np.pad(support.astype(np.uint8), 1),
                                         cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
        alpha *= np.minimum(distance / feather, 1.0)
    result = target.copy()
    weights = alpha[support, None]
    result[support] = np.rint(warped[support] * weights + target[support] * (1 - weights)).astype(np.uint8)
    encoded = io.BytesIO()
    Image.fromarray(result).save(encoded, format="PNG")
    with Image.open(io.BytesIO(encoded.getvalue())) as saved:
        reloaded = np.array(saved.convert("RGB"))
    preserved = bool(np.array_equal(reloaded[~support], target[~support]))
    if not preserved:
        raise AssertionError("Unmasked pixels changed")
    report = {
        "source_sha256": digest(source_path), "target_sha256": digest(target_path),
        "mask_sha256": digest(mask_path),
        "output_sha256": hashlib.sha256(encoded.getvalue()).hexdigest(),
        "size": [int(target.shape[1]), int(target.shape[0])],
        "repair_support_pixels": int(support.sum()),
        "changed_pixels": int(np.any(result != target, axis=2).sum()),
        "outside_mask_unchanged": preserved, "feather_inside_pixels": feather,
        "homography_source_to_target": matrix.tolist(),
        "max_control_point_error_pixels": residual,
        "visual_review": "required; pixel preservation does not prove visual correctness",
    }
    # Exclusive creation protects inputs and historical output versions.
    with output.open("xb") as stream:
        stream.write(encoded.getvalue())
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "target", "mask", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--aligned", action="store_true")
    group.add_argument("--points", type=Path)
    parser.add_argument("--feather", type=float, default=0)
    parser.add_argument("--max-error", type=float, default=2)
    args = parser.parse_args()
    try:
        report = repair(args.source, args.target, args.mask, args.output,
                        aligned=args.aligned, points_path=args.points,
                        feather=args.feather, max_error=args.max_error)
    except (ValueError, KeyError, OSError, cv2.error) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
