// Assemble a small generated pigment mark on untouched inherited rock.
const fs=require('node:fs'),zlib=require('node:zlib'),crypto=require('node:crypto');
const {decode,encode,thumbnail}=require('../../line-1/media/finish-wall.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const sig=Buffer.from('89504e470d0a1a0a','hex');

function rgba(bytes){
  if(!bytes.subarray(0,8).equals(sig))throw Error('PNG required');
  let w,h,parts=[];
  for(let p=8;p<bytes.length;){
    const n=bytes.readUInt32BE(p),t=bytes.toString('ascii',p+4,p+8),v=bytes.subarray(p+8,p+8+n);
    if(t==='IHDR'){
      w=v.readUInt32BE(0);h=v.readUInt32BE(4);
      if(w>2048||h>2048||w<1||h<1||v[8]!==8||v[9]!==6||v[12]!==0)throw Error('8-bit RGBA noninterlaced PNG required');
    }
    if(t==='IDAT')parts.push(v);
    p+=n+12;if(t==='IEND')break;
  }
  const stride=w*4,raw=zlib.inflateSync(Buffer.concat(parts),{maxOutputLength:(stride+1)*h});
  if(raw.length!==(stride+1)*h)throw Error('bad PNG raster');
  const pixels=Buffer.alloc(stride*h);
  for(let y=0;y<h;y++){
    const filter=raw[y*(stride+1)];if(filter>4)throw Error('bad PNG filter');
    for(let x=0;x<stride;x++){
      const i=y*stride+x,a=x>=4?pixels[i-4]:0,b=y?pixels[i-stride]:0,c=y&&x>=4?pixels[i-stride-4]:0;
      const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);
      const pred=[0,a,b,Math.floor((a+b)/2),pa<=pb&&pa<=pc?a:pb<=pc?b:c][filter];
      pixels[i]=(raw[y*(stride+1)+x+1]+pred)&255;
    }
  }
  return {width:w,height:h,pixels};
}

const oldBytes=fs.readFileSync('artifacts/line-4/wall-v15.png');
const record34=JSON.parse(fs.readFileSync('dist/line-4/34.json'));
if(record34.image!=='https://api.imd.fun/artifacts/'+sha(oldBytes))throw Error('ancestor hash mismatch');
const old=decode(oldBytes),glyph=rgba(fs.readFileSync('artifacts/line-4/wall-v16.png'));
const out={...old,pixels:Buffer.from(old.pixels)};
const box=[970,520,150,100];let changed=0;
for(let y=0;y<box[3];y++)for(let x=0;x<box[2];x++){
  // Supersample each scaled pixel to keep the handmade grain and worn edges.
  let alpha=0,r=0,g=0,b=0;
  for(let sy=0;sy<4;sy++)for(let sx=0;sx<4;sx++){
    const gx=Math.min(glyph.width-1,Math.floor((x+(sx+.5)/4)*glyph.width/box[2]));
    const gy=Math.min(glyph.height-1,Math.floor((y+(sy+.5)/4)*glyph.height/box[3]));
    const i=(gy*glyph.width+gx)*4,a=glyph.pixels[i+3]/255;
    alpha+=a;r+=a*glyph.pixels[i];g+=a*glyph.pixels[i+1];b+=a*glyph.pixels[i+2];
  }
  alpha/=16;if(alpha<.06)continue;
  const j=((box[1]+y)*old.width+box[0]+x)*3,src=[r/(alpha*16),g/(alpha*16),b/(alpha*16)];
  const stone=(old.pixels[j]+old.pixels[j+1]+old.pixels[j+2])/765;
  const opacity=alpha*(.62+.16*stone);
  for(let k=0;k<3;k++)out.pixels[j+k]=Math.round(old.pixels[j+k]*(1-opacity)+src[k]*opacity);
  if(!out.pixels.subarray(j,j+3).equals(old.pixels.subarray(j,j+3)))changed++;
}
if(changed<200||changed>box[2]*box[3])throw Error('unexpected pigment area');
const png=encode(out),jpg=thumbnail(out);
if(!decode(png).pixels.equals(out.pixels)||jpg.length>100000)throw Error('output codec check failed');
fs.writeFileSync('artifacts/line-4/wall-v16.png',png);
fs.unlinkSync('artifacts/line-4/wall.png');
fs.linkSync('artifacts/line-4/wall-v16.png','artifacts/line-4/wall.png');
fs.writeFileSync('dist/line-4/35.jpg',jpg);
const record={name:'The Sheltered Receipt',image:'https://api.imd.fun/artifacts/'+sha(png),attributes:[
  {trait_type:'Cave',value:'Lava'},
  {trait_type:'Wall',value:'Line 4'},
  {trait_type:'Number',value:35},
  {trait_type:'Left behind',value:'FallbackHeaders'},
  {trait_type:'Meaning',value:'An ochre shelter guards a dark receipt, like a promised header surviving every answer.'},
  {trait_type:'One thing',value:'Detect breaking OpenAPI changes'}]};
fs.writeFileSync('dist/line-4/35.json',JSON.stringify(record,null,2)+'\n');
const review={ancestor_sha256:sha(oldBytes),sha256:sha(png),dimensions:[old.width,old.height],
  format:'RGB PNG',wall:'artifacts/line-4/wall-v16.png',canonical_wall:'artifacts/line-4/wall.png',
  preview:'dist/line-4/35.jpg',preview_format:'JPEG',preview_dimensions:[512,512],
  preview_bytes:jpg.length,addition_bounds:[...box],changed_pixels:changed,
  pixels_changed_outside_addition:0,png_roundtrip_passed:true,
  method:'Built-in image generation of transparent pigment; only the small motif is blended onto the exact prior wall.',
  visual_review:'Pending visual inspection.',unmet_visual_requirements:[]};
fs.writeFileSync('line-4/review-35.json',JSON.stringify(review,null,2)+'\n');
console.log(JSON.stringify({sha256:sha(png),png_bytes:png.length,jpeg_bytes:jpg.length,
  dimensions:review.dimensions,changed_pixels:changed},null,2));
