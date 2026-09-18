export const noiseGLSL = /* glsl */`
float hash21(vec2 p) {
  p = fract(p * vec2(123.34, 345.45));
  p += dot(p, p + 34.345);
  return fract(p.x * p.y);
}
float noise2(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash21(i), hash21(i + vec2(1, 0)), f.x),
    mix(hash21(i + vec2(0, 1)), hash21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 rotation = mat2(0.8, -0.6, 0.6, 0.8);
  for (int i = 0; i < 5; i++) {
    v += a * noise2(p);
    p = rotation * p * 2.03 + 13.17;
    a *= 0.5;
  }
  return v;
}
`;

export const windGLSL = /* glsl */`
vec2 windAt(vec2 p, float time) {
  float gust = sin(p.x * .115 + p.y * .085 - time * .83);
  float detail = sin(p.x * .67 - p.y * .34 + time * 1.7);
  float swell = sin(p.y * .04 - time * .32);
  return vec2(.14 + gust * .12 + detail * .025, .075 * swell + gust * .06);
}
`;

export const riceVertex = /* glsl */`
uniform float uTime;
uniform float uWind;
attribute vec4 aPlant;
attribute float aShade;
attribute float aPart;
varying vec3 vWorld;
varying vec3 vNormal;
varying vec2 vUv;
varying float vShade;
varying float vPart;
varying float vHeight;
${windGLSL}
void main() {
  float c = cos(aPlant.w), s = sin(aPlant.w);
  mat3 turn = mat3(c, 0, -s, 0, 1, 0, s, 0, c);
  vec3 local = turn * (position * aPlant.z);
  vec2 wind = windAt(aPlant.xy, uTime) * uWind;
  float flex = pow(clamp(position.y / 1.45, 0.0, 1.0), 2.0);
  local.xz += wind * flex;
  local.y -= length(wind) * flex * .12;
  vWorld = local + vec3(aPlant.x, .025, aPlant.y);
  vNormal = normalize(turn * normal + vec3(-wind.x * flex, 0, -wind.y * flex));
  vUv = uv;
  vPart = aPart;
  vShade = aShade;
  vHeight = clamp(position.y / 1.45, 0.0, 1.0);
  gl_Position = projectionMatrix * viewMatrix * vec4(vWorld, 1.0);
}
`;

export const riceFragment = /* glsl */`
uniform vec3 uSun;
uniform vec3 uFog;
uniform float uFogDensity;
uniform float uFade;
varying vec3 vWorld;
varying vec3 vNormal;
varying vec2 vUv;
varying float vShade;
varying float vPart;
varying float vHeight;
void main() {
  vec3 n = normalize(vNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 eye = normalize(cameraPosition - vWorld);
  float diffuse = abs(dot(n, uSun));
  float transmission = pow(max(dot(-eye, uSun), 0.0), 3.0) * .52;
  float variation = fract(vShade * 7.17);
  vec3 green = mix(vec3(.035, .082, .014), vec3(.20, .27, .043), vShade);
  vec3 base = mix(green, vec3(.30, .25, .083), step(.5, vPart));
  base *= .72 + .28 * vHeight;
  // A narrow midrib and longitudinal veins catch light on each curved blade.
  float midrib = exp(-abs(vUv.x - .5) * 70.0) * .12;
  float veins = pow(abs(sin(vUv.x * 38.0)), 12.0) * .025;
  float edge = pow(abs(vUv.x - .5) * 2.0, 7.0) * .09;
  base += vec3(.12, .17, .055) * (midrib + veins + edge) * (1.0 - step(.5, vPart));
  float occlusion = mix(.26, 1.0, smoothstep(.03, .95, vHeight));
  vec3 lighting = vec3(.62, .76, .68) * .72 + vec3(1.5, 1.26, .72) * diffuse;
  vec3 color = base * lighting * occlusion;
  color += vec3(.16, .24, .042) * transmission * vHeight;
  vec3 halfway = normalize(uSun + eye);
  color += vec3(.32, .30, .14) * pow(max(dot(n, halfway), 0.0), 44.0) * .21;
  color *= .89 + variation * .21;
  float distanceToEye = length(cameraPosition - vWorld);
  float fog = 1.0 - exp(-distanceToEye * uFogDensity);
  gl_FragColor = vec4(mix(color, uFog, fog), mix(.18, 1.0, uFade));
}
`;

export const skyVertex = /* glsl */`
varying vec3 vDirection;
void main() {
  vDirection = position;
  vec4 p = projectionMatrix * mat4(mat3(viewMatrix)) * modelMatrix * vec4(position, 1.0);
  gl_Position = p.xyww;
}
`;

export const skyFragment = /* glsl */`
uniform float uTime;
uniform vec3 uSun;
varying vec3 vDirection;
${noiseGLSL}
void main() {
  vec3 ray = normalize(vDirection);
  float height = max(ray.y, 0.0);
  float horizon = exp(-height * 5.5);
  vec3 color = mix(vec3(.16, .34, .47), vec3(.75, .78, .69), horizon);
  float sunDistance = max(dot(ray, uSun), 0.0);
  color += vec3(1.0, .66, .29) * pow(sunDistance, 12.0) * .28;
  color += vec3(1.0, .76, .39) * pow(sunDistance, 95.0) * .42;
  color += vec3(9.0, 7.5, 4.5) * smoothstep(.99979, .99994, sunDistance);
  if (ray.y > .035) {
    vec2 cloudUv = ray.xz / (ray.y + .22) * 2.1 + vec2(uTime * .004, 0.0);
    float cloud = fbm(cloudUv * 1.8);
    float wisps = fbm(cloudUv * vec2(1.2, 5.5) + 34.0);
    float density = smoothstep(.48, .77, cloud * .72 + wisps * .28);
    density *= smoothstep(.035, .18, ray.y) * .72;
    vec3 cloudColor = mix(vec3(.63, .71, .72), vec3(1.08, .98, .77), pow(sunDistance, 5.0));
    color = mix(color, cloudColor, density);
  }
  color = mix(vec3(.51, .58, .46), color, smoothstep(-.05, .03, ray.y));
  gl_FragColor = vec4(color, 1.0);
}
`;

export const groundVertex = /* glsl */`
varying vec3 vWorld;
void main() {
  vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
  gl_Position = projectionMatrix * viewMatrix * vec4(vWorld, 1.0);
}
`;

export const groundFragment = /* glsl */`
uniform vec3 uFog;
uniform float uFogDensity;
varying vec3 vWorld;
${noiseGLSL}
void main() {
  vec2 p = vWorld.xz;
  // No tiled grid in the terrain itself: visible parcel edges are real curved
  // bund meshes. The ground only supplies damp, varied crop colour underneath.
  vec2 warped = p + vec2(
    sin(p.y * .039 + p.x * .019) * 2.35 + sin(p.y * .118 - p.x * .041) * .72,
    sin(p.x * .045 - p.y * .017) * 1.78 + sin(p.x * .132 + p.y * .027) * .58
  );
  float field = fbm(warped * .037);
  float grain = noise2(p * 21.0);
  float broad = fbm(warped * .072);
  vec3 crop = mix(vec3(.052, .105, .018), vec3(.255, .30, .072), smoothstep(.23, .78, field));
  float rows = smoothstep(.45, .64, abs(sin(warped.x * 8.7 + warped.y * .19)));
  crop *= .68 + .29 * broad + .10 * rows;
  vec3 earth = mix(vec3(.055, .053, .023), vec3(.21, .19, .095), broad + grain * .2);
  vec3 color = mix(crop, earth, smoothstep(.76, .95, noise2(warped * .23)) * .16);
  color *= .88 + grain * .24;
  float hill = smoothstep(1.0, 48.0, vWorld.y);
  vec3 upland = mix(vec3(.16, .19, .095), vec3(.29, .31, .18), fbm(p * .022));
  upland *= .72 + .28 * smoothstep(-.8, .8, sin(vWorld.y * .18 + p.x * .015));
  color = mix(color, upland, hill);
  float fog = 1.0 - exp(-length(cameraPosition - vWorld) * uFogDensity);
  gl_FragColor = vec4(mix(color, uFog, fog), 1.0);
}
`;

export const parcelVertex = /* glsl */`
attribute vec3 color;
varying vec3 vColor;
varying vec3 vWorld;
varying vec3 vNormal;
void main() {
  vColor = color;
  vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
  vNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * viewMatrix * vec4(vWorld, 1.0);
}
`;

export const parcelFragment = /* glsl */`
uniform vec3 uSun;
uniform vec3 uFog;
uniform float uFogDensity;
varying vec3 vColor;
varying vec3 vWorld;
varying vec3 vNormal;
${noiseGLSL}
void main() {
  vec2 p = vWorld.xz;
  float broad = fbm(p * .045);
  float fine = noise2(p * 1.85);
  float rowsA = .5 + .5 * sin(p.x * 5.7 + p.y * .19);
  float rowsB = .5 + .5 * sin(p.y * 4.9 - p.x * .16);
  float rowPattern = mix(rowsA, rowsB, smoothstep(.42, .62, broad));
  float planting = smoothstep(.47, .76, rowPattern) * .075;
  float damp = smoothstep(.76, .94, fbm(p * .12 + 17.0));
  vec3 soil = vec3(.12, .105, .052);
  vec3 crop = vColor * (.74 + broad * .36 + fine * .035);
  crop += vec3(.055, .065, .012) * planting;
  crop = mix(crop, soil, damp * .16);
  float diffuse = .52 + max(dot(normalize(vNormal), normalize(uSun)), 0.0) * .48;
  vec3 color = crop * diffuse;
  float distanceToEye = length(cameraPosition - vWorld);
  float fog = 1.0 - exp(-distanceToEye * uFogDensity);
  gl_FragColor = vec4(mix(color, uFog, fog), 1.0);
}
`;

export const gradeShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uAmount: { value: .18 } },
  vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uAmount;
    varying vec2 vUv;
    void main() {
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      vec2 p = (vUv - .5) * 1.45;
      float vignette = 1.0 - dot(p, p) * uAmount;
      float grain = fract(sin(dot(vUv * 983.1 + uTime, vec2(12.9898, 78.233))) * 43758.5453);
      c = c * vignette + (grain - .5) * .004;
      gl_FragColor = vec4(c, 1.0);
    }
  `,
};
