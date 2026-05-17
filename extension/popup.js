document.getElementById("version").textContent = chrome.runtime.getManifest().version;

chrome.tabs.query({ url: "https://web.whatsapp.com/*" }, (tabs) => {
  document.getElementById("wa-status").textContent =
    tabs.length > 0 ? "Abierto ✓" : "No abierto";
});
