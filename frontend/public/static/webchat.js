(function () {
  function getCurrentScript() {
    if (document.currentScript) {
      return document.currentScript;
    }
    var scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  }

  var script = getCurrentScript();
  if (!script) {
    return;
  }

  var botId = script.getAttribute("data-bot");
  if (!botId) {
    return;
  }

  var origin = "";
  try {
    origin = new URL(script.src).origin;
  } catch (e) {
    origin = "";
  }

  var container = document.createElement("div");
  container.style.position = "fixed";
  container.style.bottom = "24px";
  container.style.right = "24px";
  container.style.zIndex = "2147483647";
  container.style.fontFamily = "Arial, sans-serif";

  var button = document.createElement("button");
  button.type = "button";
  button.textContent = "Чат";
  button.style.background = "#2563eb";
  button.style.color = "#ffffff";
  button.style.border = "none";
  button.style.borderRadius = "999px";
  button.style.padding = "12px 18px";
  button.style.cursor = "pointer";
  button.style.boxShadow = "0 8px 20px rgba(37, 99, 235, 0.3)";

  var iframe = document.createElement("iframe");
  iframe.src = origin + "/embed/webchat/" + botId;
  iframe.style.width = "360px";
  iframe.style.height = "520px";
  iframe.style.border = "1px solid #e5e7eb";
  iframe.style.borderRadius = "16px";
  iframe.style.display = "none";
  iframe.style.marginTop = "12px";
  iframe.style.background = "#ffffff";

  var isOpen = false;

  button.addEventListener("click", function () {
    isOpen = !isOpen;
    iframe.style.display = isOpen ? "block" : "none";
  });

  container.appendChild(iframe);
  container.appendChild(button);
  document.body.appendChild(container);
})();
