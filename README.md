# RADVEM

Radar didatico com varredura eletromecanica, desenvolvido para Raspberry Pi 4
Model B.

## Equipe

- Gabriel Barrochelo; 22.10193-4
- Ruth Romeu Ramos; 22.01003-3
- Vinicius Eloy Araujo; 22.01026-2

## Apresentacao

[Video do projeto](https://mauabr-my.sharepoint.com/:v:/g/personal/22_01026-2_maua_br/IQCVvv75TYhwQJXoWr_qHLo0AcjH3mTAMmMyXW0rdlmhDQ0?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=1gfOAm)

## Hardware

O codigo usa numeracao BCM:

- GPIO 18: sinal do servo SG90.
- GPIO 23: TRIG do HC-SR04.
- GPIO 24: ECHO do HC-SR04, conectado por divisor/conversor de nivel de 5 V
  para 3.3 V.
- GND comum entre Raspberry Pi, sensor e fonte externa do servo.
- Alimentar o servo por uma fonte externa de 5 V; nao alimentar o servo pelo
  pino 3.3 V do Raspberry Pi.
- A interface deste software e grafica (Tkinter), exibida em monitor conectado
  ao Raspberry Pi. O display OLED e o botao fisico descritos em documentos
  anteriores nao sao usados pelo software atual.

Confirme a pinagem antes de ligar o circuito. Nunca conecte o ECHO de 5 V
diretamente ao GPIO do Raspberry Pi.

## Instalacao e execucao

Use Raspberry Pi OS com ambiente grafico e Python 3. Instale as dependencias
de hardware disponibilizadas pelo sistema (`gpiozero` e `lgpio`) e o Tkinter
para a versao de Python utilizada.

Na raiz deste repositorio:

```sh
python3 src/main.py
```

A janela apresenta a varredura e deteccoes recentes. Use o botao para iniciar
ou parar a aquisicao; fechar a janela encerra os recursos do radar.

Os testes automatizados que nao exigem hardware podem ser executados na raiz:

```sh
python3 -m unittest discover -s tests -v
```

## API

O cliente HTTP e executado em uma thread separada, mas a integracao permanece
desativada por padrao (`API_ENABLED = False` em `src/config.py`). Antes de
ativa-la, configure a URL real e confirme com o backend o contrato do JSON,
autenticacao e respostas esperadas. O cliente envia o evento completo em JSON,
usa timeout configuravel e registra falhas; nao faz repeticoes nem grava fila
em disco.

## Mais contexto

Consulte `RADVEM_ARQUITETURA_SOFTWARE.md` no diretorio pai para decisoes de
arquitetura, comportamento esperado e plano de desenvolvimento.
