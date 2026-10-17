// Repack round 35's finished wall for the source upload limit. No new marks.
// The nearest four-level RGB sample changes each channel by at most two units.
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const {decode, thumbnail} = require('../../line-1/media/finish-wall.cjs');

const wall = 'artifacts/line-4/wall.png';
const output = 'artifacts/line-4/wall-v16.png';
const jpeg = 'dist/line-4/35.jpg';
const recordPath = 'dist/line-4/35.json';
const reviewPath = 'line-4/review-35.json';
const signature = Buffer.from('89504e470d0a1a0a', 'hex');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function crc32(bytes) {
  let value = 0xffffffff;
  for (const byte of bytes) {
    value ^= byte;
    for (let i = 0; i < 8; i++) value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  }
  return (value ^ 0xffffffff) >>> 0;
}
function chunk(type, bytes) {
  const payload = Buffer.concat([Buffer.from(type), bytes]);
  const result = Buffer.alloc(payload.length + 8);
  result.writeUInt32BE(bytes.length, 0);
  payload.copy(result, 4);
  result.writeUInt32BE(crc32(payload), result.length - 4);
  return result;
}
function paeth(a, b, c) {
  const p = a + b - c;
  const da = Math.abs(p - a), db = Math.abs(p - b), dc = Math.abs(p - c);
  return da <= db && da <= dc ? a : db <= dc ? b : c;
}
function encode(image) {
  const {width, height, pixels} = image;
  const stride = width * 3, raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    let bestScore = Infinity, bestRow;
    for (const filter of [1, 2, 3, 4]) {
      const row = Buffer.alloc(stride + 1);
      row[0] = filter;
      let score = 0;
      for (let x = 0; x < stride; x++) {
        const i = y * stride + x;
        const a = x >= 3 ? pixels[i - 3] : 0;
        const b = y ? pixels[i - stride] : 0;
        const c = y && x >= 3 ? pixels[i - stride - 3] : 0;
        const prediction = filter === 1 ? a : filter === 2 ? b : filter === 3 ? Math.floor((a + b) / 2) : paeth(a, b, c);
        const delta = (pixels[i] - prediction) & 255;
        row[x + 1] = delta;
        score += delta < 128 ? delta : 256 - delta;
      }
      if (score < bestScore) { bestScore = score; bestRow = row; }
    }
    bestRow.copy(raw, y * (stride + 1));
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 2;
  return Buffer.concat([signature, chunk('IHDR', header), chunk('IDAT', zlib.deflateSync(raw, {level: 9, memLevel: 9})), chunk('IEND', Buffer.alloc(0))]);
}

const before = fs.readFileSync(wall), image = decode(before);
let alteredSamples = 0, maxSampleError = 0;
for (let i = 0; i < image.pixels.length; i++) {
  const old = image.pixels[i];
  const next = Math.min(255, Math.round(old / 4) * 4);
  image.pixels[i] = next;
  if (next !== old) alteredSamples++;
  maxSampleError = Math.max(maxSampleError, Math.abs(next - old));
}
const png = encode(image), check = decode(png);
if (!check.pixels.equals(image.pixels) || maxSampleError > 2) throw Error('PNG round trip or sample error failed');
const jpg = thumbnail(image);
if (jpg.length > 100000) throw Error('JPEG too large');
// Use separate writes: the incoming canonical wall and named output may be hard links.
fs.writeFileSync(output + '.new', png);
fs.renameSync(output + '.new', output);
fs.writeFileSync(wall + '.new', png);
fs.renameSync(wall + '.new', wall);
fs.writeFileSync(jpeg, jpg);
const record = JSON.parse(fs.readFileSync(recordPath, 'utf8'));
record.image = 'https://api.imd.fun/artifacts/' + sha(png);
fs.writeFileSync(recordPath, JSON.stringify(record, null, 2) + '\n');
const review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));
review.sha256 = sha(png);
review.preview_bytes = jpg.length;
const methodNote = ' Final PNG uses a four-unit RGB color grid and adaptive row filters to meet the upload limit.';
if (!review.method.includes(methodNote)) review.method += methodNote;
const firstRepack = review.repack;
review.repack = {source_bytes: firstRepack?.source_bytes ?? before.length,
  output_bytes: png.length,
  altered_samples: firstRepack?.altered_samples ?? alteredSamples,
  max_sample_error: firstRepack?.max_sample_error ?? maxSampleError};
fs.writeFileSync(reviewPath, JSON.stringify(review, null, 2) + '\n');
console.log(JSON.stringify({sha256: sha(png), png_bytes: png.length, jpeg_bytes: jpg.length, altered_samples: alteredSamples, max_sample_error: maxSampleError}));
