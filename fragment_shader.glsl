#version 330 core

in vec3 vColor;
in vec2 TexCoord;
in vec3 FragPos;

out vec4 FragColor;

uniform sampler2D textura1;

uniform vec3 lightPos;      // Onde a luz está
uniform vec3 lightDir;      // Para onde aponta
uniform float cutOff;       // Ângulo interno (luz forte)
uniform float outerCutOff;  // Ângulo externo (onde a luz morre)
uniform vec3 ambientLight;  // Cor da escuridão (fora da luz)
uniform vec3 lightColor;    // Cor da luz

void main(){
    // FragColor = texture(textura1, TexCoord) * vec4(vColor, 1.0);
    // Se a coordenada UV for (0,0), assume-se que é uma lateral sem textura
    vec4 baseColor;
    if (TexCoord.x <= 0.001 && TexCoord.y <= 0.001) {
        baseColor = vec4(vColor, 1.0); // Cor pura nas laterais
    } else {
        // Mistura a textura com a cor do topo
        vec4 texColor = texture(textura1, TexCoord);
        baseColor = vec4(texColor.rgb * vColor, 1.0); 
    }

    // 2. Cálculo do Cone
    vec3 lightToFrag = normalize(lightPos - FragPos);
    float theta = dot(lightToFrag, normalize(-lightDir));
    
    // 3. Suavização (Anti tela-preta)
    float epsilon = cutOff - outerCutOff;
    float intensity = 0.0;
    if (epsilon > 0.0001) { 
        intensity = clamp((theta - outerCutOff) / epsilon, 0.0, 1.0);
    }

    // 4. Resultado Final
    vec3 finalLighting = ambientLight + vec3(lightColor * intensity);
    finalLighting = clamp(finalLighting, 0.0, 1.0);

    FragColor = vec4(baseColor.rgb * finalLighting, baseColor.a); 
}