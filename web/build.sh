#!/bin/bash
set -e
mkdir -p dist
sed \
  -e "s|%%FIREBASE_API_KEY%%|${FIREBASE_API_KEY:-YOUR_API_KEY}|g" \
  -e "s|%%FIREBASE_PROJECT_ID%%|${FIREBASE_PROJECT_ID:-YOUR_PROJECT_ID}|g" \
  index.html > dist/index.html
echo "Build complete → dist/index.html"
