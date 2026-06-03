

##Nomes/RAs:
Gabriel Barrochelo; 22.10193-4
Ruth Romeu Ramos; 22.01003-3
Vinícius Eloy Araujo; 22.01026-2

## Link do vídeo
https://mauabr-my.sharepoint.com/:v:/g/personal/22_01026-2_maua_br/IQCVvv75TYhwQJXoWr_qHLo0AcjH3mTAMmMyXW0rdlmhDQ0?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=1gfOAm

## 🔌 Conexões físicas
### 🎛️ Botão
GPIO 1 → botão  
Outro terminal do botão → 3.3V  
Utilizando PULL_DOWN interno do Pico  
### 📟 Display OLED (SSD1306 - I2C)
GPIO 4 (SDA) → SDA do display  
GPIO 5 (SCL) → SCL do display  
3.3V → VCC  
GND → GND  
### 🔄 Servo Motor (SG90)
GPIO 15 → sinal (fio laranja/amarelo)  
Fonte externa 5V → VCC (fio vermelho)  
GND da fonte → GND (fio marrom/preto)  

### ⚠️ Observações:
Servo alimentado externamente  
GND da fonte conectado ao GND do Pico (obrigatório)  
### 📡 Sensor Ultrassônico (HC-SR04)
Lado do sensor:  
GPIO 2 → TRIG  
ECHO → conversor de nível lógico (lado 5V)  
5V → VCC  
GND → GND  
### 🔁 Conversor de nível lógico (3.3V ↔ 5V)
HV (High Voltage) → 5V  
LV (Low Voltage) → 3.3V  
GND → GND comum  
Sinais:  
ECHO (sensor) → HV (entrada 5V)  
LV (saída convertida) → GPIO 3 do Pico  

👉 TRIG não precisa passar pelo conversor (3.3V já é suficiente para o sensor)  

### 🔗 GND comum (essencial)

Todos os GNDs devem estar conectados:  
Pico  
Fonte do servo  
Sensor ultrassônico  
Display  
Conversor de nível lógico  


<img width="1920" height="1080" alt="Quadro Branco de Diagrama de Planejamento de Fluxo de Trabalho em Roxo Azul Estilo Moderno Profissional" src="https://github.com/user-attachments/assets/64be7fb4-6607-4b64-8eed-249249a4be1a" />

