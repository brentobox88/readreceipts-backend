        # Save incoming bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        # Convert HEIC to JPEG if needed, then resize + compress for Qwen
        jpg_path = tmp_path + ".jpg"
        try:
            img = Image.open(tmp_path)

            # Convert to RGB (handles HEIC, PNG with alpha, etc.)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize so the longest edge is at most 1600px
            max_dim = 1600
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                logger.info(f"Resized image from {w}x{h} to {img.size}")

            # Save as JPEG with compression
            img.save(jpg_path, "JPEG", quality=80, optimize=True)
            logger.info(f"Compressed to {os.path.getsize(jpg_path)} bytes")
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            jpg_path = tmp_path