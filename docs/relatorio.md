# Relatório Técnico — Turtle Draw

## 1. Visão Geral

O projeto **Turtle Draw** implementa uma pipeline de visão computacional utilizando apenas NumPy para processamento matemático e ROS 2 para integração com o turtlesim. O objetivo é extrair contornos de uma imagem e convertê-los em trajetórias desenhadas pela tartaruga.

A aplicação foi desenvolvida com foco educacional, priorizando a implementação manual das etapas principais da pipeline em vez do uso direto de funções prontas do OpenCV.

---

## 2. Decisões de Implementação da Pipeline

### 2.1 Conversão RGB para Escala de Cinza

A conversão para grayscale foi implementada utilizando os pesos perceptuais do padrão ITU-R BT.601:

```text
Gray = 0.299R + 0.587G + 0.114B
```

Essa abordagem foi escolhida porque preserva melhor a percepção de luminosidade humana em comparação com uma média simples dos canais RGB.

---

### 2.2 Suavização com Blur Gaussiano

Foi utilizado um filtro Gaussiano com kernel 15×15 e σ=3.5 para reduzir ruídos antes da detecção de bordas.

Durante os testes, kernels menores mantinham muitos artefatos da imagem original, enquanto valores maiores removiam detalhes importantes. O tamanho escolhido apresentou melhor equilíbrio entre suavização e preservação dos contornos principais.

---

### 2.3 Detecção de Bordas

A detecção de bordas foi implementada manualmente utilizando os operadores de Sobel para cálculo dos gradientes horizontais e verticais.

Após o cálculo do gradiente, foi aplicada Non-Maximum Suppression para afinar as bordas e, em seguida, histerese com limiares duplos (`low_ratio` e `high_ratio`) para reduzir falsos positivos.

A escolha dessa abordagem teve como objetivo evitar o uso direto do algoritmo Canny do OpenCV, permitindo maior entendimento e controle sobre cada etapa da pipeline.

---

### 2.4 Extração de Contornos

Os contornos foram extraídos utilizando o algoritmo Moore-Neighbor Tracing, responsável por percorrer pixels conectados em oito direções.

Essa estratégia foi escolhida para garantir que cada contorno fosse armazenado como uma sequência ordenada de coordenadas, facilitando o desenho posterior no turtlesim.

Além disso, foram adicionados filtros por tamanho mínimo (`min_contour_len`) e compactação da bounding box para remover ruídos e contornos espalhados pela imagem.

---

### 2.5 Mapeamento para o Turtlesim

As coordenadas dos contornos foram normalizadas para o espaço do turtlesim, que possui dimensões de aproximadamente 11×11 unidades.

Também foi necessário inverter o eixo Y, pois imagens utilizam origem no canto superior esquerdo, enquanto o turtlesim utiliza origem no canto inferior esquerdo.

---

## 3. Dificuldades Encontradas

### 3.1 Aplicação Duplicada de Blur

Durante o desenvolvimento, o blur Gaussiano estava sendo aplicado duas vezes: uma antes da detecção de bordas e outra internamente na função responsável pelos gradientes.

Isso gerava excesso de suavização e perda de detalhes importantes da imagem. O problema foi identificado utilizando visualização intermediária da pipeline e corrigido removendo a segunda aplicação do filtro.

---

### 3.2 Ruídos Excessivos nos Contornos

Inicialmente, muitos contornos indesejados eram detectados em regiões de textura da imagem.

Para solucionar o problema, foram adicionados filtros por comprimento mínimo de contorno e compactação da bounding box. Esses filtros reduziram significativamente a quantidade de ruído detectado.

---

### 3.3 Inversão do Eixo Y

Na primeira versão do projeto, os desenhos apareciam invertidos verticalmente no turtlesim.

O problema ocorreu devido à diferença entre o sistema de coordenadas das imagens e o sistema utilizado pelo simulador. A correção foi realizada invertendo o eixo Y durante o mapeamento das coordenadas.

---

## 4. Conclusão

O projeto permitiu implementar e compreender manualmente etapas clássicas de visão computacional, incluindo convolução, detecção de bordas, rastreamento de contornos e normalização de coordenadas.

Apesar de bibliotecas como OpenCV fornecerem implementações prontas para essas operações, a construção manual da pipeline possibilitou maior entendimento dos algoritmos envolvidos e maior flexibilidade para ajustes específicos do projeto.