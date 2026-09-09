// Минимальный стаб браузерного окружения для прогона app.js под Node —
// без него автотестов у ванильного JS-фронтенда вообще не было (см.
// CLAUDE.md, "фронтенд не покрыт автотестами"). НЕ полноценный jsdom —
// осознанно: только то, что реально трогает app.js, чтобы не тащить
// в проект новую зависимость ради этого. getElementById по-настоящему
// проверяет наличие id="..." в последнем отрендеренном HTML (как в
// браузере), а не слепо возвращает фейковый узел — именно так поймали
// реальный краш "Команда" после "Команда → Турниры → Команда"
// (см. CLAUDE.md, "Найден и исправлен реальный краш").
"use strict";

function installDomStub() {
  var currentHtml = "";

  function makeFakeElement(id) {
    return {
      id: id,
      _listeners: {},
      value: "",
      addEventListener: function (evt, fn) { this._listeners[evt] = fn; },
      classList: { toggle: function () {}, add: function () {}, remove: function () {} },
      focus: function () {},
      getAttribute: function () { return null; }
    };
  }

  var root = {
    set innerHTML(v) { currentHtml = v; },
    get innerHTML() { return currentHtml; }
  };

  global.document = {
    getElementById: function (id) {
      if (id === "app") return root;
      var re = new RegExp('id="' + id + '"');
      if (!re.test(currentHtml)) return null;
      return makeFakeElement(id);
    },
    querySelectorAll: function (selector) {
      var results = [];
      if (selector.indexOf("[data-nav]") !== -1) {
        var re = /data-nav="([^"]+)"/g, m;
        while ((m = re.exec(currentHtml))) {
          (function (navKey) {
            var el = makeFakeElement("nav-" + navKey);
            el.getAttribute = function (name) { return name === "data-nav" ? navKey : null; };
            results.push(el);
          })(m[1]);
        }
      }
      // Остальные querySelectorAll-вызовы в app.js (.book-btn, .team-join-btn,
      // .challenge-candidate и т.п.) используются только когда реально есть
      // карточки — пустой массив безопасен по конструкции (.forEach на []
      // никогда не бросает), поэтому не эмулируем их построчно здесь.
      return results;
    },
    querySelector: function (selector) {
      // Только class-селекторы вида ".foo" — этого хватает для
      // bindScrollFade(document.querySelector(".filters-row-wrap"), ...)
      // (единственный реальный вызов document.querySelector в app.js).
      if (selector.charAt(0) === "." ) {
        var cls = selector.slice(1);
        var re = new RegExp('class="[^"]*\\b' + cls + '\\b[^"]*"');
        if (re.test(currentHtml)) return makeFakeElement("__qs__" + cls);
      }
      return null;
    },
    createElement: function () { return makeFakeElement("__toast__"); },
    addEventListener: function () {},
    body: { appendChild: function () {} }
  };

  global.localStorage = {
    _data: {},
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(this._data, k) ? this._data[k] : null; },
    setItem: function (k, v) { this._data[k] = v; },
    removeItem: function (k) { delete this._data[k]; }
  };

  // Node 24+ уже определяет глобальный navigator/fetch сам (только getter,
  // без setter) — переопределяем через defineProperty, простое присваивание
  // здесь падает с "Cannot set property navigator of ... which has only a getter".
  Object.defineProperty(global, "navigator", { value: { clipboard: null }, configurable: true, writable: true });
  global.window = global;

  return {
    getCurrentHtml: function () { return currentHtml; }
  };
}

module.exports = { installDomStub: installDomStub };
