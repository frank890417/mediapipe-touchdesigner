// 雙手黑洞：兩隻手的手掌中心各一個黑洞（周圍空間被吸進去），兩手靠近時中間打開一個洞，露出另一個畫面
// 輸入 0：原畫面（攝影機）　輸入 1：洞裡要出現的畫面（例：上堂的場景）
uniform vec4 uH1;     // x, y（0~1）, active, radius
uniform vec4 uH2;
uniform vec4 uPortal; // mid x, mid y, open（0~1）, aspect
out vec4 fragColor;

vec2 lens(vec2 uv, vec2 c, float r, float aspect) {
    vec2 d = (uv - c) * vec2(aspect, 1.0);
    float dist = length(d);
    // 越靠近黑洞，取樣點越往外推 ⇒ 看起來像周圍空間被吸進去
    float pull = r * r / max(dist, 1e-4) * 1.6;
    float k = smoothstep(r * 4.0, r, dist);
    vec2 dir = d / max(dist, 1e-4);
    d += dir * pull * k;
    return c + d / vec2(aspect, 1.0);
}

void main() {
    vec2 uv = vUV.st;
    float aspect = uPortal.w;
    vec2 suv = uv;
    float hole = 0.0;
    if (uH1.z > 0.5) {
        suv = lens(suv, uH1.xy, uH1.w, aspect);
        float d1 = length((uv - uH1.xy) * vec2(aspect, 1.0));
        hole = max(hole, 1.0 - smoothstep(uH1.w * 0.85, uH1.w, d1));
    }
    if (uH2.z > 0.5) {
        suv = lens(suv, uH2.xy, uH2.w, aspect);
        float d2 = length((uv - uH2.xy) * vec2(aspect, 1.0));
        hole = max(hole, 1.0 - smoothstep(uH2.w * 0.85, uH2.w, d2));
    }
    vec4 base = texture(sTD2DInputs[0], suv);
    vec4 other = texture(sTD2DInputs[1], uv);
    // 兩手靠近 ⇒ 中間的洞打開，洞裡是另一個畫面
    float pr = uPortal.z * 0.6;
    float dp = length((uv - uPortal.xy) * vec2(aspect, 1.0));
    float portal = 1.0 - smoothstep(pr * 0.9, pr, dp);
    // 黑洞邊緣一圈亮光（事件視界）
    float rim = 0.0;
    if (uH1.z > 0.5) { float d1 = length((uv - uH1.xy) * vec2(aspect, 1.0)); rim += exp(-pow((d1 - uH1.w) / (uH1.w * 0.08 + 1e-4), 2.0)); }
    if (uH2.z > 0.5) { float d2 = length((uv - uH2.xy) * vec2(aspect, 1.0)); rim += exp(-pow((d2 - uH2.w) / (uH2.w * 0.08 + 1e-4), 2.0)); }
    vec3 col = mix(base.rgb, vec3(0.0), hole) + vec3(1.0, 0.75, 0.4) * rim * 0.8;
    float prim = exp(-pow((dp - pr) / (pr * 0.06 + 1e-4), 2.0)) * step(0.001, uPortal.z);
    col = mix(col, other.rgb, portal) + vec3(0.6, 0.8, 1.0) * prim;
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
