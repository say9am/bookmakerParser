Простой асинхронный WebSocket сервер, построенный с использованием библиотек Python `websockets` и `asyncio`. Этот сервер управляет клиентскими подключениями, отправляет случайный JSON-файл (конфигурация для трекера старницы матча) при подключении, логирует взаимодействия с клиентами и предоставляет базовую структуру для обработки входящих сообщений.

## Возможные улучшения

*   **Реализация авторизации клиентов:** После того как клиент подключился и аутентифицировался, необходимо внедрить механизм **авторизации**. Это позволит **контролировать доступ** клиента к различным функциям или данным на сервере.
*   **Создание хранилища данных клиентов для управления и логирования:** Разработать систему для **постоянного хранения информации о клиентах** (независимо от того, подключены они в данный момент или нет). Такое хранилище должно как минимум содержать:
    *   **Уникальный идентификатор** для каждого клиента.
    *   **Индивидуальный журнал (лог) активности** для каждого клиента, куда будут записываться важные события, связанные именно с ним (например, время подключения/отключения, отправленные/полученные команды, возникшие ошибки).
Это позволит **управлять клиентами по отдельности** (например, просматривать их историю, статус, возможно, применять какие-то настройки) и **анализировать их поведение или отлаживать проблемы**, просматривая логи конкретного пользователя, а не общий поток событий сервера. В качестве хранилища можно использовать базу данных (SQL или NoSQL).



## Описание структуры: 

В директории `server/track_commands/` находятся конфигурации для трекеров страниц матча. Сервер случайным образом выберет один из них для отправки новым клиентам.

    *Пример `server/track_commands/sample_track.json`:*
    ```json
    {
      "command": "track",
      "config": {
        "url": "https://sbbet.me/sport",
        "navigation_steps": {
          "steps": [
            {
              "action": "click",
              "coordinate": [
                124,
                266
              ],
              "path": null
            },
            {
              "action": "scroll",
              "coordinate": [
                124,
                266
              ],
              "value": [
                0,
                131
              ]
            },
            {
              "action": "click",
              "coordinate": [
                101,
                247
              ],
              "path": null
            },
            {
              "action": "click",
              "coordinate": [
                102,
                328
              ],
              "path": null
            },
            {
              "action": "click",
              "coordinate": [
                478,
                318
              ],
              "path": null
            },
            {
              "action": "click",
              "coordinate": [
                689,
                379
              ],
              "path": null
            }
          ]
        },
        "navigation_steps_additional": {
          "steps": [
            {
              "action": "click",
              "coordinate": [
                162,
                22
              ],
              "path": null
            },
            {
              "action": "click",
              "coordinate": [
                171,
                90
              ],
              "path": null
            }
          ]
        },
        "load_criteria": [
          {
            "path": "#root > div.App > div.sport:nth-of-type(2) > div.bordered-right:nth-of-type(1) > div.responsive > div.from-desktop.flex.sidebar-sports.d-flex.flex-column > div.sidebar.sidebar__bordered-right:nth-of-type(2) > div.sports-sidebar > div.sports-sidebar__sports-wrapper:nth-of-type(1) > div.loader-wrapper > div.accordion",
            "count": 3
          }
        ],
        "track_area": {
              "path": "#frame-wrapper > div.all-odds-overlay__markets-wrapper:nth-of-type(1) > div.all-odds-overlay__odds-markets:nth-of-type(2)"
        }
      }
    }
    ```
## Скрипт для получения инструкции навигации:

```javascript
(() => {
    let navigationSteps = [];
    let scrollStartData = null; // { element, startScrollX, startScrollY, clientX, clientY }
    let scrollTimeout = null;
    const SCROLL_DELAY = 500;

    // --- Helper Function: Найти первый прокручиваемый родительский элемент ---
    function findScrollableParent(element) {
        if (!element) { return window; }
        let current = element;
        while (current && current !== document.body && current !== document.documentElement) {
            const style = window.getComputedStyle(current);
            const overflowY = style.overflowY;
            const overflowX = style.overflowX;
            const isScrollableY = overflowY !== 'visible' && overflowY !== 'hidden';
            const isScrollableX = overflowX !== 'visible' && overflowX !== 'hidden';
            const canScrollY = current.scrollHeight > current.clientHeight + 1;
            const canScrollX = current.scrollWidth > current.clientWidth + 1;
            if ((isScrollableY && canScrollY) || (isScrollableX && canScrollX)) {
                return current;
            }
            current = current.parentElement;
        }
        return window;
    }

    // --- Helper Function: Форматирование даты UTC в строку YYYY-MM-DD_HH-MM-SS ---
    function getFormattedUtcTimestamp(date) {
        const year = date.getUTCFullYear();
        // getUTCMonth() возвращает 0-11, нам нужны 1-12
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        const hours = String(date.getUTCHours()).padStart(2, '0');
        const minutes = String(date.getUTCMinutes()).padStart(2, '0');
        const seconds = String(date.getUTCSeconds()).padStart(2, '0');

        return `${year}-${month}-${day}_${hours}-${minutes}-${seconds}`;
    }


    function addStep(action, details) {
        if (details.value) {
            details.value = [Math.round(details.value[0]), Math.round(details.value[1])];
        }
        let targetInfo = "(Scroll target: window)";
        if (details.targetElement && details.targetElement !== window) {
             targetInfo = `(Scroll target: ${details.targetElement.tagName}#${details.targetElement.id || ''}.${details.targetElement.className || ''})`;
             delete details.targetElement; // Удаляем несериализуемый элемент
        } else {
             delete details.targetElement;
        }

        navigationSteps.push({ action, ...details });
        // Логируем после добавления и удаления targetElement
        console.log("Added step:", navigationSteps[navigationSteps.length - 1]);
        console.log(`   ${targetInfo}`);
    }

    // Отслеживание кликов
    document.addEventListener('click', (event) => {
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
            scrollTimeout = null;
            scrollStartData = null;
            console.log("Scroll cancelled due to click.");
        }
        addStep('click', {
            coordinate: [event.clientX, event.clientY],
            path: null // Пока не записываем path
        });
    }, { capture: true });

    // Отслеживание колесика мыши
    document.addEventListener('wheel', (event) => {
        if (!scrollTimeout) {
            const scrollableElement = findScrollableParent(event.target);
            let startScrollX, startScrollY;
            if (scrollableElement === window) {
                startScrollX = window.scrollX;
                startScrollY = window.scrollY;
            } else {
                startScrollX = scrollableElement.scrollLeft;
                startScrollY = scrollableElement.scrollTop;
            }
            scrollStartData = {
                element: scrollableElement,
                startScrollX: startScrollX,
                startScrollY: startScrollY,
                clientX: event.clientX,
                clientY: event.clientY
            };
             const targetDesc = scrollableElement === window ? "Window" : `Element ${scrollableElement.tagName}`;
             console.log(`Scroll sequence started on ${targetDesc} at (${startScrollX}, ${startScrollY})`);
        }

        if (scrollTimeout) { clearTimeout(scrollTimeout); }

        scrollTimeout = setTimeout(() => {
            if (scrollStartData) {
                let endScrollX, endScrollY;
                const element = scrollStartData.element;
                if (element === window) {
                    endScrollX = window.scrollX;
                    endScrollY = window.scrollY;
                } else {
                    if (!document.contains(element)) {
                         console.warn("Scroll target element no longer exists. Cancelling scroll step.");
                         scrollTimeout = null; scrollStartData = null; return;
                    }
                    endScrollX = element.scrollLeft;
                    endScrollY = element.scrollTop;
                }
                const effectiveDeltaX = endScrollX - scrollStartData.startScrollX;
                const effectiveDeltaY = endScrollY - scrollStartData.startScrollY;
                console.log(`Scroll sequence ended. Effective Delta: (${effectiveDeltaX}, ${effectiveDeltaY})`);
                if (Math.abs(effectiveDeltaX) > 0.5 || Math.abs(effectiveDeltaY) > 0.5) {
                    addStep('scroll', {
                        coordinate: [scrollStartData.clientX, scrollStartData.clientY],
                        value: [effectiveDeltaX, effectiveDeltaY],
                        targetElement: element // Передаем для логирования в addStep
                    });
                } else {
                    console.log("Scroll delta too small, step not added.");
                }
            }
            scrollTimeout = null; scrollStartData = null;
        }, SCROLL_DELAY);
    }, { passive: true });

    // Сохранение при закрытии страницы
    window.addEventListener('beforeunload', () => {
        // Фиксация последнего скролла (если был)
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
             if (scrollStartData) {
                let endScrollX, endScrollY;
                const element = scrollStartData.element;
                 if (element === window) {
                    endScrollX = window.scrollX; endScrollY = window.scrollY;
                } else if (document.contains(element)) {
                    endScrollX = element.scrollLeft; endScrollY = element.scrollTop;
                }
                 if (typeof endScrollX !== 'undefined' && typeof endScrollY !== 'undefined') {
                     const effectiveDeltaX = endScrollX - scrollStartData.startScrollX;
                     const effectiveDeltaY = endScrollY - scrollStartData.startScrollY;
                     console.log(`Finalizing pending scroll on unload. Effective Delta: (${effectiveDeltaX}, ${effectiveDeltaY})`);
                     if (Math.abs(effectiveDeltaX) > 0.5 || Math.abs(effectiveDeltaY) > 0.5) {
                         addStep('scroll', {
                             coordinate: [scrollStartData.clientX, scrollStartData.clientY],
                             value: [effectiveDeltaX, effectiveDeltaY],
                             targetElement: element // Для логирования
                         });
                     }
                 } else {
                     console.warn("Could not finalize scroll on unload, target element might be gone.");
                 }
            }
        }

        // --- Код сохранения файла с новым именем ---
        if (navigationSteps.length > 0) {
            try {
                // --- Генерация имени файла на основе UTC ---
                const now = new Date();
                const timestamp = getFormattedUtcTimestamp(now); // Используем хелпер
                const filename = `${timestamp}.json`; // Формат: YYYY-MM-DD_HH-MM-SS.json
                console.log(`Generating filename (UTC): ${filename}`);
                // --- Конец генерации имени файла ---

                const json = JSON.stringify({ steps: navigationSteps }, null, 2);
                const blob = new Blob([json], { type: 'application/json' });
                const url = URL.createObjectURL(blob);

                const a = document.createElement('a');
                a.href = url;
                a.download = filename; // <<< Устанавливаем новое имя файла
                document.body.appendChild(a);
                a.click();

                // Небольшая задержка перед очисткой, чтобы скачивание успело начаться
                setTimeout(() => {
                    if (document.body.contains(a)) { // Проверка, что элемент еще в DOM
                       document.body.removeChild(a);
                    }
                    URL.revokeObjectURL(url);
                    console.log("JSON file download initiated.");
                }, 100);

            } catch (error) {
                console.error("Error saving navigation steps:", error);
            }
        }
    });

    console.log("Скрипт отслеживания кликов и ИЗМЕРЕННОГО скролла (окно/элемент) с UTC именем файла запущен.");
})();
```

## Скрипт для получения элемента, откуда извлекаются ставки:

```javascript
(function() {
    'use strict';

    // Используем Map для хранения {элемент: исходныйЦветФона}
    let highlightedElementsMap = new Map();
    const storageKey = 'lastClickedElementPath'; // Ключ для sessionStorage
    const highlightColor = 'rgba(255, 0, 0, 0.4)'; // Цвет выделения (чуть менее насыщенный)

    /**
     * Генерирует CSS-селектор для элемента.
     * @param {Element} el - DOM-элемент.
     * @returns {string} - Сгенерированный CSS-селектор.
     */
    function getCssSelector(el) {
        // ... (код getCssSelector остается без изменений) ...
        if (!(el instanceof Element)) return;
        const path = [];
        while (el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.nodeName.toLowerCase();
            if (el.id) {
                selector = '#' + CSS.escape(el.id.trim());
                path.unshift(selector);
                break;
            } else {
                let sibling = el;
                let nth = 1;
                while (sibling = sibling.previousElementSibling) {
                    if (sibling.nodeName.toLowerCase() === selector) nth++;
                }

                const classes = Array.from(el.classList)
                                   .map(cls => cls.trim())
                                   .filter(cls => cls !== '')
                                   .map(cls => '.' + CSS.escape(cls));
                selector += classes.join('');

                const parent = el.parentNode;
                let addNthOfType = false;
                if (parent && parent.nodeType === Node.ELEMENT_NODE) {
                     const siblingsOfType = Array.from(parent.children).filter(child => child.nodeName.toLowerCase() === el.nodeName.toLowerCase());
                    if (siblingsOfType.length > 1) {
                        addNthOfType = true;
                    }
                } else if (!parent) {
                    addNthOfType = false;
                } else {
                     addNthOfType = false;
                }

                if (addNthOfType) {
                     selector += `:nth-of-type(${nth})`;
                }
            }
            path.unshift(selector);
            if (el.parentNode && el.parentNode.nodeType === Node.ELEMENT_NODE) {
                el = el.parentNode;
            } else {
                break;
            }
        }
        return path.join(' > ');
    }

    /**
     * Снимает выделение со всех ранее выделенных элементов.
     */
    function unhighlightAll() {
        highlightedElementsMap.forEach((originalBg, element) => {
            try {
                // Восстанавливаем исходный цвет фона
                element.style.backgroundColor = originalBg;
            } catch (e) {
                // Элемент мог быть удален из DOM
                console.warn("Не удалось сбросить стиль для элемента (возможно, удален):", element, e);
            }
        });
        // Очищаем Map для следующего выделения
        highlightedElementsMap.clear();
    }

    /**
     * Применяет стиль для выделения элемента и всех его потомков.
     * @param {Element} targetElement - Элемент, по которому кликнули.
     */
    function highlightElementAndDescendants(targetElement) {
        // 1. Снимаем предыдущее выделение
        unhighlightAll();

        // 2. Собираем все элементы для выделения: сам элемент + все его потомки
        const elementsToHighlight = [targetElement, ...targetElement.querySelectorAll('*')];

        // 3. Проходим по всем элементам, сохраняем их исходный фон и применяем новый
        elementsToHighlight.forEach(element => {
            // Убедимся, что это действительно элемент (на всякий случай)
            if (element.nodeType === Node.ELEMENT_NODE) {
                // Сохраняем текущий вычисленный цвет фона
                const computedStyle = window.getComputedStyle(element);
                const originalBg = computedStyle.backgroundColor;
                highlightedElementsMap.set(element, originalBg); // Сохраняем в Map

                // Применяем цвет выделения (перезаписывая любые стили)
                element.style.backgroundColor = highlightColor;
            }
        });
    }

    /**
     * Инициирует скачивание файла с заданным текстом.
     * @param {string} filename - Имя файла для скачивания.
     * @param {string} text - Текст, который будет содержимым файла.
     */
    function triggerDownload(filename, text) {
        // ... (код triggerDownload остается без изменений) ...
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log(`Файл '${filename}' скачан.`);
    }

    // --- Обработчик клика ---
    document.addEventListener('click', function(event) {
        const targetElement = event.target;

        if (!targetElement || !(targetElement instanceof Element)) {
            return;
        }
        if (targetElement.closest('#element-path-notifier')) {
            return;
        }

        // 1. Выделяем элемент и всех его потомков
        highlightElementAndDescendants(targetElement);

        // 2. Генерируем путь для *кликнутого* элемента
        const selectorPath = getCssSelector(targetElement);
        console.log('Выбранный элемент (клик):', targetElement);
        console.log('Сгенерированный путь:', selectorPath);

        // 3. Сохраняем путь в sessionStorage
        if (selectorPath) {
            try {
                sessionStorage.setItem(storageKey, selectorPath);
                console.log(`Путь '${selectorPath}' сохранен в sessionStorage.`);
            } catch (e) {
                console.error("Не удалось сохранить путь в sessionStorage:", e);
            }
        }
        // event.preventDefault();
        // event.stopPropagation(); // Оставил закомментированным, но может понадобиться

    }, true); // true - фаза захвата

    // --- Логика при загрузке страницы (уведомление) ---
    window.addEventListener('DOMContentLoaded', () => {
        // ... (код уведомления остается без изменений) ...
        const savedPath = sessionStorage.getItem(storageKey);
        if (savedPath) {
            console.log(`Найден сохраненный путь из предыдущей сессии: ${savedPath}`);
            const container = document.createElement('div');
            container.id = 'element-path-notifier';
            container.style.cssText = `
                position: fixed; bottom: 10px; left: 10px;
                background-color: rgba(255, 255, 224, 0.95); border: 1px solid #ccc;
                border-radius: 4px; padding: 12px 15px; z-index: 10000;
                font-size: 14px; font-family: Arial, sans-serif;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.25); max-width: 90%; color: #333;
            `; // Используем cssText для компактности

            const textNode = document.createTextNode('Найден путь к элементу: ');
            const pathNode = document.createElement('code');
            pathNode.textContent = savedPath;
            pathNode.style.cssText = `
                background-color: #e8e8e8; padding: 3px 5px; border-radius: 3px;
                margin: 0 5px; color: #000; word-break: break-all;
            `;

            const buttonContainer = document.createElement('div');
            buttonContainer.style.cssText = `
                margin-top: 10px; display: flex; gap: 10px;
            `;

            const downloadButton = document.createElement('button');
            downloadButton.textContent = 'Скачать путь';
            downloadButton.style.cssText = `
                padding: 5px 10px; cursor: pointer; border: 1px solid #bbb;
                border-radius: 3px; background-color: #f0f0f0;
            `;

            const closeButton = document.createElement('button');
            closeButton.textContent = 'Закрыть';
            closeButton.style.cssText = downloadButton.style.cssText; // Используем тот же стиль

            downloadButton.onclick = (e) => {
                e.stopPropagation();
                triggerDownload('element_path.txt', savedPath);
                sessionStorage.removeItem(storageKey);
                console.log(`Путь '${savedPath}' удален из sessionStorage.`);
                container.remove();
            };

             closeButton.onclick = (e) => {
                 e.stopPropagation();
                 container.remove();
                 // sessionStorage.removeItem(storageKey); // Опционально: удалить при закрытии
             };

            container.appendChild(textNode);
            container.appendChild(pathNode);
            buttonContainer.appendChild(downloadButton);
            buttonContainer.appendChild(closeButton);
            container.appendChild(buttonContainer);
            document.body.appendChild(container);
        } else {
            console.log('Сохраненный путь в sessionStorage не найден.');
        }
    });

})(); // Запускаем IIFE
```
