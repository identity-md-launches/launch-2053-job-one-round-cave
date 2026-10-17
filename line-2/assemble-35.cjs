// One-time media assembly: keep only the generated addition on bare rock.
// All reads and writes stay in this workspace; no network or secret access.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('../line-1/media/finish-wall.cjs');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
if (fs.existsSync('dist/line-2/35.json')) throw Error('record 35 already exists');
const prior = fs.readFileSync('artifacts/line-2/wall.png');
if (hash(prior) !== 'c30106ab04442c94d3c21ffc4a7a31d977614dab03ea04c48529476bf5fb273f')
  throw Error('round-34 wall changed');
const candidate = fs.readFileSync('artifacts/line-2/wall-v16.png');
const old = decode(prior), generated = decode(candidate);
if (old.width !== 1254 || old.height !== 1254 ||
    generated.width !== old.width || generated.height !== old.height)
  throw Error('wall dimensions changed');
const output = {...old, pixels: Buffer.from(old.pixels)};
// This bare right-side patch excludes the inherited upper basket and leaves.
const bounds = {left: 990, top: 390, right: 1160, bottom: 555};
const feather = 9;
for (let y = bounds.top; y < bounds.bottom; y++) {
  for (let x = bounds.left; x < bounds.right; x++) {
    const edge = Math.min(x-bounds.left, bounds.right-1-x,
                          y-bounds.top, bounds.bottom-1-y);
    const alpha = Math.max(0, Math.min(1, edge / feather));
    const i = (y*old.width+x)*3;
    for (let c = 0; c < 3; c++) output.pixels[i+c] =
      Math.round(old.pixels[i+c]*(1-alpha) + generated.pixels[i+c]*alpha);
  }
}
let changed = 0, outside = 0;
for (let y = 0; y < old.height; y++) for (let x = 0; x < old.width; x++) {
  const i = (y*old.width+x)*3;
  if (!old.pixels.subarray(i,i+3).equals(output.pixels.subarray(i,i+3))) {
    changed++;
    if (x < bounds.left || x >= bounds.right || y < bounds.top || y >= bounds.bottom) outside++;
  }
}
if (!changed || outside) throw Error('preservation check failed');
const png = encode(output), jpg = thumbnail(output);
if (!decode(png).pixels.equals(output.pixels)) throw Error('PNG roundtrip failed');
if (jpg.length > 100000) throw Error('preview exceeds 100 KB');
fs.writeFileSync('artifacts/line-2/wall-v16.png', png);
fs.writeFileSync('artifacts/line-2/wall.png', png);
fs.writeFileSync('dist/line-2/35.jpg', jpg);
const report = {previous_sha256: hash(prior), sha256: hash(png),
  format: 'PNG', width: old.width, height: old.height, png_bytes: png.length,
  preview_format: 'JPEG', preview_width: 512, preview_height: 512,
  preview_bytes: jpg.length, bounds, feather, changed_pixels: changed,
  outside_mark_changed_pixels: outside, png_roundtrip_passed: true,
  unmet_visual_requirements: []};
fs.writeFileSync('line-2/media-check-35.json', JSON.stringify(report,null,2)+'\n');
const record = {name: 'The Joining Bowl',
  image: 'https://api.imd.fun/artifacts/' + hash(png),
  attributes: [{trait_type:'Cave',value:'Lava'},
    {trait_type:'Wall',value:'Line 2'}, {trait_type:'Number',value:35},
    {trait_type:'Left behind',value:'ZipMerge'},
    {trait_type:'Meaning',value:'Two trails of stones join in one bowl without collision.'},
    {trait_type:'One thing',value:'Safely extract untrusted ZIP archives with explicit path and resource limits'}]};
fs.writeFileSync('dist/line-2/35.json', JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
