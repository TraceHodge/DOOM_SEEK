import cv2
import numpy as np

def find_best_overlap(img_left, img_right, search_ratio=0.5):
    """
    Finds the best horizontal overlap between two images
    by minimizing mean squared error (MSE) of overlapping pixels.
    """
    gray_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
    gray_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)

    max_offset = int(gray_left.shape[1] * search_ratio)
    best_offset = 0
    best_score = float("inf")

    for offset in range(20, max_offset):
        left_overlap = gray_left[:, -offset:]
        right_overlap = gray_right[:, :offset]
        if left_overlap.shape[1] != right_overlap.shape[1]:
            continue
        diff = np.mean((left_overlap.astype(np.float32) - right_overlap.astype(np.float32)) ** 2)
        if diff < best_score:
            best_score = diff
            best_offset = offset

    return best_offset


def blend_overlap(region_left, region_right):
    """
    Smoothly blends two overlapping image regions together using linear alpha blending.
    """
    width = region_left.shape[1]
    alpha = np.linspace(0, 1, width, dtype=np.float32)
    alpha = np.tile(alpha, (region_left.shape[0], 1))
    alpha = np.expand_dims(alpha, axis=2)
    blended = (region_left * (1 - alpha) + region_right * alpha).astype(np.uint8)
    return blended


def stitch_four_panorama(left_path, midL_path, midR_path, right_path):
    """Creates a straight, seamlessly blended panorama from four images."""
    # Load images
    left = cv2.imread(left_path)
    midL = cv2.imread(midL_path)
    midR = cv2.imread(midR_path)
    right = cv2.imread(right_path)

    # Resize all to the same height
    target_height = 600
    def resize_keep_ratio(img):
        h, w = img.shape[:2]
        scale = target_height / h
        return cv2.resize(img, (int(w * scale), target_height))

    left, midL, midR, right = [resize_keep_ratio(i) for i in [left, midL, midR, right]]

    # Compute best overlaps between consecutive pairs
    overlap_L_ML = find_best_overlap(left, midL)
    overlap_ML_MR = find_best_overlap(midL, midR)
    overlap_MR_R = find_best_overlap(midR, right)

    # Compute total panorama width
    pano_width = (
        left.shape[1]
        + midL.shape[1] - overlap_L_ML
        + midR.shape[1] - overlap_ML_MR
        + right.shape[1] - overlap_MR_R
    )
    panorama = np.zeros((target_height, pano_width, 3), dtype=np.uint8)

    # --- Place and blend LEFT + MID-L ---
    panorama[:, :left.shape[1]] = left
    start_L_ML = left.shape[1] - overlap_L_ML
    left_part = panorama[:, start_L_ML:left.shape[1]]
    midL_part = midL[:, :overlap_L_ML]
    blended_L_ML = blend_overlap(left_part, midL_part)
    panorama[:, start_L_ML:left.shape[1]] = blended_L_ML
    panorama[:, left.shape[1]:left.shape[1] + (midL.shape[1] - overlap_L_ML)] = midL[:, overlap_L_ML:]

    # --- Blend MID-L + MID-R ---
    start_ML_MR = left.shape[1] + (midL.shape[1] - overlap_L_ML) - overlap_ML_MR
    midL_part2 = panorama[:, start_ML_MR:start_ML_MR + overlap_ML_MR]
    midR_part = midR[:, :overlap_ML_MR]
    blended_ML_MR = blend_overlap(midL_part2, midR_part)
    panorama[:, start_ML_MR:start_ML_MR + overlap_ML_MR] = blended_ML_MR
    panorama[:, start_ML_MR + overlap_ML_MR:start_ML_MR + overlap_ML_MR + (midR.shape[1] - overlap_ML_MR)] = midR[:, overlap_ML_MR:]

    # --- Blend MID-R + RIGHT ---
    start_MR_R = start_ML_MR + (midR.shape[1] - overlap_ML_MR) - overlap_MR_R
    midR_part2 = panorama[:, start_MR_R:start_MR_R + overlap_MR_R]
    right_part = right[:, :overlap_MR_R]
    blended_MR_R = blend_overlap(midR_part2, right_part)
    panorama[:, start_MR_R:start_MR_R + overlap_MR_R] = blended_MR_R
    panorama[:, start_MR_R + overlap_MR_R:start_MR_R + overlap_MR_R + (right.shape[1] - overlap_MR_R)] = right[:, overlap_MR_R:]

    return panorama


if __name__ == "__main__":
    # File paths for four images
    left_img = "left_pan2.jpeg"
    midL_img = "midL_pan2.jpeg"
    midR_img = "midR_pan2.jpeg"
    right_img = "right_pan2.jpeg"

    # Generate panorama
    result = stitch_four_panorama(left_img, midL_img, midR_img, right_img)

    # Save and show result
    save_path = "panorama_4_blended.jpg"
    cv2.imwrite(save_path, result)
    print(f"✅ Panorama saved as {save_path}")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
