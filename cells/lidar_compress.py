def process(input_data):
    # Delta encoding for LIDAR scans
    scan = input_data["scan"]  # [dist1, dist2,...]
    compressed = [scan[0]]
    for i in range(1, len(scan)):
        delta = scan[i] - scan[i-1]
        compressed.append(delta if abs(delta) < 5 else scan[i])
    return {"compressed_scan": compressed, "original_size": len(scan)}
