# Image matching — what exists and how to extend it

**Implemented:** `ImageEmbedder` in `backend/app/matching.py` converts each photo to a normalised 3×8-bin RGB colour histogram; similarity is histogram intersection (Swain & Ballard, 1991). The photo signal participates in the score only when both items have local photos and has default weight 0.10. It detects "similar overall colours", **not** object identity — a red phone and a red book look alike.

**Not implemented (future work):** deep-learning embeddings.

**Extension point:** subclass `ImageEmbedder`, override `embed(path)` (return a vector) and `similarity(a, b)` (return 0..1), and assign it to `matching.EMBEDDER`. Example plan:
1. `pip install torch torchvision` (or `onnxruntime` + a CLIP/ResNet ONNX model).
2. `embed`: resize/normalise, run the model, L2-normalise the feature vector; cache vectors in a new `image_embeddings` table.
3. `similarity`: cosine similarity mapped to 0..1.
4. Re-run `/api/admin/rematch`, then evaluate on a labelled set *with photos* before claiming any improvement.
