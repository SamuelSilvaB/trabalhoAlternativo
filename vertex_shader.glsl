#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uMVP;
uniform mat4 modelMatrix;

out vec3 vColor;
out vec2 TexCoord;
out vec3 FragPos;

void main(){
    gl_Position = uMVP * vec4(aPos, 1.0);
    FragPos = vec3(modelMatrix * vec4(aPos, 1.0));
    vColor = aColor;
    TexCoord = aTexCoord;
}