#!/usr/bin/env bash
set -e
cd frontend
npm install
npm run build

# Copy static files to the standalone directory so the Next.js standalone server can serve them
cp -r .next/static .next/standalone/.next/
cp -r public .next/standalone/
