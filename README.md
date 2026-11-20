# LED Controller – User Guide (English / Русский)

## Languages:
- [English](#english)
- [Русский](#русский)

---

# English

> **⚠️ Important:** LED Controller talks to the strip **directly over Bluetooth LE**.  
> A BLE strip accepts **only one connection at a time** — close the phone app (Magic Home, LED BLE, etc.) and disconnect the strip from the phone **before** running LED Controller.

---

## What is LED Controller?

LED Controller is a desktop tool for Windows, macOS and Linux that controls Bluetooth LED strips (ELK‑BLEDOM / MELK / Triones family).  
It sends raw commands straight into the strip's GATT characteristic `0000fff3-0000-1000-8000-00805f9b34fb`, so no vendor app and no cloud account are needed.

You get one power switch, an RGB picker, saved colour presets, and a list of your own strips with individual settings for each.

---

## Requirements

- Windows 10 / 11, macOS 11+, or Linux with BlueZ 5.43+  
- A Bluetooth adapter with **BLE (Bluetooth 4.0+)** support  
- An LED strip controlled over the `fff3` characteristic (ELK‑BLEDOM and clones)  
- The strip **not connected** to a phone or another app

---

## Installation & Running

After building, you get two folders:

- `output-window-dir/LEDController/` – **recommended** (no console window)  
- `output-console-dir-debug/LEDController/` – **debug version** (shows a console with error messages)

### How to run

1. Go to the folder you want to use.  
2. Double‑click `LEDController.exe` (Windows) or `LEDController` (macOS / Linux).

**If something goes wrong:** run the **console version** – connection errors, write errors and tracebacks will appear in the black window. You can copy them to get help.

### Create a desktop shortcut (optional)

**Windows**

- **Method 1:** Right‑click `LEDController.exe` → **Send to** → **Desktop (create shortcut)**.  
- **Method 2:** Right‑click on an empty area of your desktop → **New** → **Shortcut** → Click **Browse** → select `LEDController.exe` → click **Next** → give it a name → click **Finish**.

**macOS:** drag the app to **Applications**, then hold **⌥⌘** and drag it to the Desktop to make an alias.  
**Linux:** create a `.desktop` file in `~/.local/share/applications/` pointing at the executable.

You can rename the shortcut however you like.

---

## How to Use

### 1. Find your strip
On the first launch the **Поиск устройств** (Device search) window opens by itself.  
The status line shows *“Сканирование Bluetooth…”* immediately, and the list fills in a few seconds later.

### 2. Save it to your devices
Tick the checkboxes next to the strips you own and press **Сохранить отмеченные**.  
A **green, locked checkbox** means the device is already saved — it cannot be ticked twice.  
Use the filter (**Все / Сохранённые / Не сохранённые**), the search box (name, MAC or UUID) and **Скрывать без имени** to cut the noise.

### 3. Pick the active strip
Open **Сохранённые устройства**, then press **Сделать активной** on the row you need.  
The active strip is marked with a green **активна** badge, and its name appears in the top‑left corner of the main window.

### 4. Power
One switch — **ON / OFF**. No separate buttons.  
The switch is greyed out while there is no connection, and comes back automatically after a reconnect.

### 5. Colour
Drag the **R / G / B** sliders and press **Применить цвет**.  
The last colour is remembered **per strip** and restored the next time you connect.

### 6. Presets
Type a name into **Имя нового пресета** and press **Сохранить** — the colour is written into the `presets` folder.  
Click a preset to apply it instantly; select one and press **Удалить** to remove the file.

### 7. Device info
Press the round **i** button under the strip name.  
A small window shows name, MAC, UUID, the address actually in use, the GATT characteristic, link state, power state, current RGB and the auto modes.

### 8. Per‑strip settings
In **Сохранённые устройства** press **Настроить** on a row:

- **Имя** – any label you like  
- **MAC** – can be typed by hand  
- **UUID** – **read‑only**, issued by the OS during scanning; use **Копировать** to copy it  
- **Включать при запуске и подключении**  
- **Выключать при закрытии приложения**  
- **Интервал переподключения, сек**

Changes are saved **immediately** — there is no “Save” button.  
**Удалить из сохранённых** always asks for confirmation.

---

## How LED Controller talks to the strip

Commands are written into characteristic `0000fff3-0000-1000-8000-00805f9b34fb`, write‑without‑response first, falling back to write‑with‑response.

| Command | Bytes |
|---------|-------|
| Power on | `7E 00 04 F0 00 01 FF 00 EF` |
| Power off | `7E 00 04 00 00 00 FF 00 EF` |
| Colour RGB | `7E 00 05 03 RR GG BB 00 EF` |

Setting a colour runs `power on → colour → pause → power on` — the last packet latches the colour on ELK‑BLEDOM firmware.  
If `fff3` is missing, the first writable characteristic is used instead (helps with `ffe1` / `ffe9` clones).

### MAC vs UUID — why the addresses look different

- **Windows / Linux** connect by **MAC**, e.g. `BE:27:D2:00:0C:D9`.  
- **macOS** connects by **UUID**, e.g. `A696D3A4-B979-44FA-6313-E4F6EAF2289E`. CoreBluetooth never exposes MAC addresses, and a UUID **cannot** be converted into a MAC — it is generated per computer.

Both fields live in the same device record, so one `settings.json` works on all three systems. The app picks the right one automatically.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Search finds nothing | Enable Bluetooth; on macOS grant **System Settings → Privacy & Security → Bluetooth** to Terminal / PyCharm / the app. |
| “Нет связи, повторим автоматически” | The strip is still connected to your phone. Close the phone app, turn Bluetooth off there, power‑cycle the strip. |
| Colour does not change | Run `TestLED.py` with the same address. If that works but the GUI does not — you picked a different device row. |
| “Write error” in the console | The strip dropped the link mid‑write. Wait for the auto‑reconnect, or press the power switch again. |
| macOS shows UUID instead of MAC | Normal. Use the UUID; press **Копировать** in the strip settings to copy it. |
| Linux: no devices / “Operation not permitted” | `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))` |
| Interface looks broken or empty | Make sure all seven `.ui` files are present in the `ui` folder next to the executable. |
| Settings or presets are not saved | The folder next to the executable must be writable — avoid `Program Files` / read‑only locations. |
| App crashes or behaves weirdly | Run the **console version** – the error messages will help. |

---

## Building from Source (for developers)

If you want to run the Python code directly:

1. Install Python 3.9+ and dependencies:  
   `pip install -r requirements.txt`  
2. Make sure `_internal/`, `ui/` (all seven `.ui` files) and `presets/` are present.  
3. Run: `python Run.py`

Smoke test without the GUI:

```bash
python TestLED.py A696D3A4-B979-44FA-6313-E4F6EAF2289E 0 0 255
```

Build two versions with PyInstaller:

```bash
pip install pyinstaller

# macOS / Linux
pyinstaller --noconsole --name LEDController --add-data "ui:ui" --add-data "presets:presets" Run.py
pyinstaller --console   --name LEDController --add-data "ui:ui" --add-data "presets:presets" Run.py

# Windows (semicolon separator)
pyinstaller --noconsole --name LEDController --add-data "ui;ui" --add-data "presets;presets" Run.py
pyinstaller --console   --name LEDController --add-data "ui;ui" --add-data "presets;presets" Run.py
```

Project layout:

```
Run.py                  entry point
TestLED.py              hardware smoke test
_internal/              logic: settings, BLE, windows, widgets
ui/                     Qt Designer files
settings/settings.json  configuration
presets/*.json          saved colours
```

---

## Notes

- Supported strips: ELK‑BLEDOM family and clones using the `fff3` characteristic  
- Settings are saved in `settings/settings.json` (next to the .exe); colours live in `presets/`  
- Behaviour settings are **per strip**, not global  
- UUID is read‑only — it comes from scanning, never typed by hand  
- Auto‑reconnect restores both power state and colour  
- No keyboard shortcuts – use the on‑screen buttons

---

Enjoy! If you need help, use the console version and share the error output.

---

# Русский

> **⚠️ Важно:** LED Controller общается с лентой **напрямую по Bluetooth LE**.  
> BLE‑лента держит **только одно соединение** — закройте приложение на телефоне (Magic Home, LED BLE и т.п.) и отключите ленту от телефона **до** запуска LED Controller.

---

## Что такое LED Controller?

LED Controller — это программа для Windows, macOS и Linux, которая управляет Bluetooth‑светодиодными лентами (семейство ELK‑BLEDOM / MELK / Triones).  
Команды отправляются прямо в GATT‑характеристику ленты `0000fff3-0000-1000-8000-00805f9b34fb`, поэтому фирменное приложение и облачный аккаунт не нужны.

В вашем распоряжении один тумблер питания, выбор цвета RGB, сохранённые пресеты и список своих лент с отдельными настройками для каждой.

---

## Системные требования

- Windows 10 / 11, macOS 11+ или Linux с BlueZ 5.43+  
- Bluetooth‑адаптер с поддержкой **BLE (Bluetooth 4.0+)**  
- Светодиодная лента, управляемая через характеристику `fff3` (ELK‑BLEDOM и клоны)  
- Лента **не подключена** к телефону или другой программе

---

## Установка и запуск

После сборки у вас будут две папки:

- `output-window-dir/LEDController/` – **рекомендуемая** (без консольного окна)  
- `output-console-dir-debug/LEDController/` – **отладочная версия** (показывает консоль с сообщениями об ошибках)

### Как запустить

1. Перейдите в нужную папку.  
2. Дважды щёлкните по `LEDController.exe` (Windows) или `LEDController` (macOS / Linux).

**Если что-то пошло не так:** запустите **консольную версию** – ошибки подключения, ошибки записи и трейсбеки появятся в чёрном окне. Их можно скопировать и отправить для помощи.

### Создать ярлык на рабочем столе (по желанию)

**Windows**

- **Способ 1:** Щёлкните правой кнопкой мыши по `LEDController.exe` → **Отправить** → **Рабочий стол (создать ярлык)**.  
- **Способ 2:** Щёлкните правой кнопкой мыши на пустом месте рабочего стола → **Создать** → **Ярлык** → Нажмите **Обзор** → выберите `LEDController.exe` → нажмите **Далее** → дайте название ярлыку → нажмите **Готово**.

**macOS:** перетащите приложение в **Программы**, затем зажмите **⌥⌘** и перетащите его на рабочий стол — получится псевдоним.  
**Linux:** создайте файл `.desktop` в `~/.local/share/applications/`, указав путь к исполняемому файлу.

Ярлык можно переименовать как угодно.

---

## Как пользоваться

### 1. Найдите ленту
При первом запуске окно **Поиск устройств** открывается само.  
Строка статуса сразу показывает *«Сканирование Bluetooth…»*, а список заполняется через несколько секунд.

### 2. Сохраните её в свои устройства
Отметьте галочками нужные ленты и нажмите **Сохранить отмеченные**.  
**Зелёная заблокированная галочка** означает, что устройство уже сохранено — повторно его отметить нельзя.  
Фильтр (**Все / Сохранённые / Не сохранённые**), строка поиска (имя, MAC или UUID) и **Скрывать без имени** убирают лишний шум.

### 3. Выберите активную ленту
Откройте **Сохранённые устройства** и нажмите **Сделать активной** на нужной строке.  
Активная лента помечается зелёным бейджем **активна**, а её имя появляется в левом верхнем углу главного окна.

### 4. Питание
Один тумблер — **ON / OFF**. Никаких двух кнопок.  
Пока нет соединения, тумблер серый; после переподключения он оживает сам.

### 5. Цвет
Двигайте слайдеры **R / G / B** и нажмите **Применить цвет**.  
Последний цвет запоминается **для каждой ленты отдельно** и восстанавливается при следующем подключении.

### 6. Пресеты
Впишите имя в **Имя нового пресета** и нажмите **Сохранить** — цвет запишется в папку `presets`.  
Клик по пресету применяет его сразу; выделите пресет и нажмите **Удалить**, чтобы убрать файл.

### 7. Информация об устройстве
Нажмите круглую кнопку **i** под именем ленты.  
Маленькое окно покажет имя, MAC, UUID, реально используемый адрес, GATT‑характеристику, состояние связи, питание, текущий RGB и авто‑режимы.

### 8. Настройки конкретной ленты
В окне **Сохранённые устройства** нажмите **Настроить** на строке:

- **Имя** – любое удобное название  
- **MAC** – можно вписать вручную  
- **UUID** – **только чтение**, выдаётся системой при сканировании; кнопка **Копировать** кладёт его в буфер  
- **Включать при запуске и подключении**  
- **Выключать при закрытии приложения**  
- **Интервал переподключения, сек**

Изменения сохраняются **сразу** — кнопки «Сохранить» нет.  
**Удалить из сохранённых** всегда спрашивает подтверждение.

---

## Как LED Controller управляет лентой

Команды пишутся в характеристику `0000fff3-0000-1000-8000-00805f9b34fb`: сначала без ответа, при отказе — с ответом.

| Команда | Байты |
|---------|-------|
| Включить | `7E 00 04 F0 00 01 FF 00 EF` |
| Выключить | `7E 00 04 00 00 00 FF 00 EF` |
| Цвет RGB | `7E 00 05 03 RR GG BB 00 EF` |

Смена цвета идёт по цепочке `включить → цвет → пауза → включить` — последний пакет закрепляет цвет на прошивке ELK‑BLEDOM.  
Если характеристики `fff3` нет, берётся первая доступная для записи — это спасает клоны с `ffe1` / `ffe9`.

### MAC и UUID — почему адреса выглядят по-разному

- **Windows / Linux** подключаются по **MAC**, например `BE:27:D2:00:0C:D9`.  
- **macOS** подключается по **UUID**, например `A696D3A4-B979-44FA-6313-E4F6EAF2289E`. CoreBluetooth не отдаёт MAC‑адреса, и UUID **нельзя** превратить в MAC — он генерируется отдельно для каждого компьютера.

Оба поля хранятся в одной записи устройства, поэтому один `settings.json` работает на всех трёх системах. Приложение само выбирает нужное.

---

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| Поиск никого не находит | Включите Bluetooth; на macOS выдайте разрешение **Системные настройки → Конфиденциальность и безопасность → Bluetooth** для Terminal / PyCharm / приложения. |
| «Нет связи, повторим автоматически» | Лента всё ещё подключена к телефону. Закройте приложение на телефоне, выключите там Bluetooth, передёрните питание ленты. |
| Цвет не меняется | Запустите `TestLED.py` с тем же адресом. Если он работает, а GUI нет — выбрана другая строка устройства. |
| «Write error» в консоли | Лента оборвала связь во время записи. Дождитесь автопереподключения или щёлкните тумблер ещё раз. |
| На macOS вместо MAC показывается UUID | Так и должно быть. Используйте UUID; кнопка **Копировать** в настройках ленты скопирует его. |
| Linux: нет устройств / «Operation not permitted» | `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))` |
| Интерфейс пустой или выглядит сломанным | Проверьте, что все семь файлов `.ui` лежат в папке `ui` рядом с исполняемым файлом. |
| Настройки и пресеты не сохраняются | Папка рядом с исполняемым файлом должна быть доступна для записи — не запускайте из `Program Files` или с read‑only диска. |
| Приложение вылетает или ведёт себя странно | Запустите **консольную версию** – сообщения об ошибках помогут. |

---

## Сборка из исходного кода (для разработчиков)

Если хотите запустить Python‑код напрямую:

1. Установите Python 3.9+ и зависимости:  
   `pip install -r requirements.txt`  
2. Убедитесь, что на месте `_internal/`, `ui/` (все семь файлов `.ui`) и `presets/`.  
3. Запустите: `python Run.py`

Проверка железа без GUI:

```bash
python TestLED.py A696D3A4-B979-44FA-6313-E4F6EAF2289E 0 0 255
```

Сборка двух версий через PyInstaller:

```bash
pip install pyinstaller

# macOS / Linux
pyinstaller --noconsole --name LEDController --add-data "ui:ui" --add-data "presets:presets" Run.py
pyinstaller --console   --name LEDController --add-data "ui:ui" --add-data "presets:presets" Run.py

# Windows (разделитель — точка с запятой)
pyinstaller --noconsole --name LEDController --add-data "ui;ui" --add-data "presets;presets" Run.py
pyinstaller --console   --name LEDController --add-data "ui;ui" --add-data "presets;presets" Run.py
```

Структура проекта:

```
Run.py                  точка входа
TestLED.py              проверка железа без GUI
_internal/              логика: настройки, BLE, окна, виджеты
ui/                     файлы Qt Designer
settings/settings.json  конфигурация
presets/*.json          сохранённые цвета
```

---

## Примечания

- Поддерживаемые ленты: семейство ELK‑BLEDOM и клоны на характеристике `fff3`  
- Настройки сохраняются в `settings/settings.json` (рядом с .exe); цвета лежат в `presets/`  
- Поведение настраивается **для каждой ленты отдельно**, а не глобально  
- UUID доступен только для чтения — он приходит из сканирования, вручную его не вписать  
- Автопереподключение восстанавливает и питание, и цвет  
- Горячие клавиши не предусмотрены – используйте кнопки на экране

---

Приятного использования! Если нужна помощь, запустите консольную версию и пришлите вывод ошибок.