// One-shot transfer of image-tool pigment; retain ancestral pixels everywhere else.
const fs=require('node:fs'), crypto=require('node:crypto');
const media=require('./png_codec.cjs');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const source='artifacts/line-3/wall-v15.png';
const proposal='artifacts/line-3/051df6f1-dee9-4649-8f23-7e5142125856-1.png';
const destination='artifacts/line-3/wall-v16.png';
if(fs.existsSync(destination)) throw Error('Refusing overwrite');
const oldBytes=fs.readFileSync(source), generatedBytes=fs.readFileSync(proposal);
if(hash(oldBytes)!=='5fddc2105f66b94fbc8db4e07a3848032939245ab1f6c3c5cba6f16a5f469696') throw Error('Wrong ancestor');
const old=media.decode(oldBytes), generated=media.decode(generatedBytes);
const out={...old,pixels:Buffer.from(old.pixels)}, box=[1018,468,110,108];
const disk=(x,y,cx,cy,r)=>Math.hypot(x-cx,y-cy)<=r;
function nearSegment(x,y,ax,ay,bx,by,r) {
  const t=Math.max(0,Math.min(1,((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)));
  return Math.hypot(x-ax-t*(bx-ax),y-ay-t*(by-ay))<=r;
}
let changed=0;
for(let y=box[1];y<box[1]+box[3];y++) for(let x=box[0];x<box[0]+box[2];x++) {
  const i=(y*old.width+x)*3, [r,g,b]=generated.pixels.subarray(i,i+3);
  const radius=Math.hypot(x-1049,y-524);
  const charcoal=radius>=17 && radius<=28 && r<115 && g<93 && b<75;
  const silhouette=disk(x,y,1049,524,16)||disk(x,y,1103,486,16)||disk(x,y,1109,553,17)
    ||nearSegment(x,y,1069,510,1094,491,6)||nearSegment(x,y,1069,536,1099,549,6);
  const red=silhouette && r>95 && r>g*1.6 && g<115 && r-b>65;
  if(!charcoal && !red) continue;
  const color=charcoal?[40,30,23]:[151,63,30], alpha=charcoal?.70:.67;
  for(let c=0;c<3;c++) out.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+color[c]*alpha);
  changed++;
}
let outside=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  if(x>=box[0]&&x<box[0]+box[2]&&y>=box[1]&&y<box[1]+box[3]) continue;
  const i=(y*old.width+x)*3;
  if(!out.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) outside++;
}
if(outside || changed<500 || changed>5000) throw Error('Preservation/motif check failed');
const bytes=media.encode(out), preview=media.thumbnail(out);
if(!media.decode(bytes).pixels.equals(out.pixels)||preview.length>100000) throw Error('Image format check failed');
fs.writeFileSync(destination,bytes,{flag:'wx'});
// Remove the link before replacing it, never write through it into the ancestor.
fs.unlinkSync('artifacts/line-3/wall.png');
fs.symlinkSync('wall-v16.png','artifacts/line-3/wall.png');
fs.writeFileSync('dist/line-3/33.jpg',preview,{flag:'wx'});
const result={source,source_sha256:hash(oldBytes),generated_sha256:hash(generatedBytes),
  output:destination,output_sha256:hash(bytes),patch_xywh:box,changed_pixels:changed,
  changed_pixels_outside_patch:outside,png_dimensions:[old.width,old.height],png_format:'RGB PNG',png_bytes:bytes.length,
  jpeg_dimensions:[512,512],jpeg_format:'JPEG',jpeg_bytes:preview.length,
  method:'Only generated motif pigment blended onto original rock inside its silhouette; no generated background copied.'};
fs.writeFileSync('line-3/asset-build/preservation-33.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
fs.unlinkSync(proposal); // Retain only the finished wall and required JPEG as new images.
console.log(JSON.stringify(result,null,2));
