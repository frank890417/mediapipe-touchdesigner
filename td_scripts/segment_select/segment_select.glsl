// segment_select：從 MediaPipe 多類別人像分割（每一區一種顏色）挑出你勾選的部位，輸出遮罩
// 輸入 0：MediaPipe 的 segmentation（上了色的分割圖）　輸入 1：攝影機畫面
// 類別顏色跟 MediaPipe 元件的 Scolor0～5 一樣（由參數帶進來）
uniform vec3 uC0; uniform vec3 uC1; uniform vec3 uC2; uniform vec3 uC3; uniform vec3 uC4; uniform vec3 uC5;
uniform vec3 uOnA;   // 背景, 頭髮, 身體皮膚
uniform vec3 uOnB;   // 臉的皮膚, 衣服, 其他（配件）
uniform vec2 uTol;   // 顏色容差, 反轉（1＝反過來）
out vec4 fragColor;

float hit(vec3 c, vec3 k) { return 1.0 - smoothstep(uTol.x * 0.5, uTol.x, distance(c, k)); }

void main() {
    vec4 s = texture(sTD2DInputs[0], vUV.st);
    vec3 c = s.rgb;
    float a = s.a;
    float m = 0.0;
    // 背景通常是透明（alpha 0），所以背景另外用 alpha 判斷
    m += uOnA.x * max(hit(c, uC0) * step(0.5, a), 1.0 - a);
    m += uOnA.y * hit(c, uC1) * a;
    m += uOnA.z * hit(c, uC2) * a;
    m += uOnB.x * hit(c, uC3) * a;
    m += uOnB.y * hit(c, uC4) * a;
    m += uOnB.z * hit(c, uC5) * a;
    m = clamp(m, 0.0, 1.0);
    m = mix(m, 1.0 - m, uTol.y);
    fragColor = TDOutputSwizzle(vec4(vec3(m), m));
}
