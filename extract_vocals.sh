#!/usr/bin/env bash
set -euo pipefail

# Extract human vocals from a video file.
# Usage: extract_vocals.sh <input.mp4> [output_dir]

INPUT="${1:?usage: extract_vocals.sh <input.mp4> [output_dir]}"
OUT_DIR="${2:-output}"
mkdir -p "$OUT_DIR"

RNNOISE_MODEL="${RNNOISE_MODEL:-$OUT_DIR/cb.rnnn}"
if [[ ! -f "$RNNOISE_MODEL" ]]; then
  curl -sL -o "$RNNOISE_MODEL" \
    "https://github.com/GregorR/rnnoise-models/raw/master/conjoined-burgers-2018-08-28/cb.rnnn"
fi

ffmpeg -y -i "$INPUT" -vn -acodec pcm_s16le -ar 44100 "$OUT_DIR/audio.wav"

ffmpeg -y -i "$OUT_DIR/audio.wav" \
  -af "highpass=f=80,lowpass=f=8000,arnndn=m=$RNNOISE_MODEL,afftdn=nr=12:nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11" \
  "$OUT_DIR/vocals.wav"

ffmpeg -y -i "$OUT_DIR/vocals.wav" -codec:a libmp3lame -b:a 192k "$OUT_DIR/vocals.mp3"

echo "Done. Output: $OUT_DIR/vocals.wav, $OUT_DIR/vocals.mp3"
