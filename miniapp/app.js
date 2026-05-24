const tg = window.Telegram?.WebApp;
const state = {
  config: null,
  isTelegramContext: false,
  toastTimer: null,
};

function $(id) {
  return document.getElementById(id);
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.hidden = false;

  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 3400);
}

function setButtonState(id, options) {
  const button = $(id);
  button.disabled = !options.enabled;
  button.textContent = options.label;
  button.classList.toggle("primary", options.primary === true);
  button.classList.toggle("muted", options.primary !== true);
}

function showDevBanner(message) {
  const banner = $("devBanner");
  const text = $("devBannerText");
  text.textContent = message;
  banner.hidden = false;
}

async function requestJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Не удалось выполнить запрос");
  }

  return data;
}

function openExternalUrl(url) {
  if (tg?.openLink) {
    tg.openLink(url);
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

function closeMiniAppIfPossible() {
  tg?.close?.();
}

async function handleStarsPayment() {
  try {
    const data = await requestJson("/miniapp/api/payment/stars-link", {
      initData: tg?.initData || "",
    });

    if (tg?.openInvoice) {
      tg.openInvoice(data.url, (status) => {
        if (status === "paid") {
          showToast("Оплата Stars прошла успешно");
          return;
        }

        if (status === "cancelled") {
          showToast("Оплата была отменена");
          return;
        }

        showToast("Счёт открыт в Telegram");
      });
      return;
    }

    openExternalUrl(data.url);
  } catch (error) {
    showToast(error.message);
  }
}

async function handleCardPayment() {
  try {
    const data = await requestJson("/miniapp/api/payment/card-link", {
      initData: tg?.initData || "",
    });

    if (!data.external && tg?.openInvoice) {
      tg.openInvoice(data.url, (status) => {
        if (status === "paid") {
          showToast("Оплата картой прошла успешно");
          return;
        }

        if (status === "cancelled") {
          showToast("Оплата была отменена");
          return;
        }

        showToast("Счёт на оплату картой открыт");
      });
      return;
    }

    openExternalUrl(data.url);
    closeMiniAppIfPossible();
  } catch (error) {
    showToast(error.message);
  }
}

async function handleCryptoPayment() {
  try {
    if (state.config?.crypto_url) {
      openExternalUrl(state.config.crypto_url);
      return;
    }

    const data = await requestJson("/miniapp/api/payment/crypto-link", {
      initData: tg?.initData || "",
    });
    openExternalUrl(data.url);
    closeMiniAppIfPossible();
  } catch (error) {
    showToast(error.message);
  }
}

function bindActions() {
  $("starsButton").addEventListener("click", handleStarsPayment);
  $("cardButton").addEventListener("click", handleCardPayment);
  $("cryptoButton").addEventListener("click", handleCryptoPayment);
}

function renderConfig(config) {
  state.config = config;

  const productTitle = $("productTitle");
  if (productTitle) {
    productTitle.textContent = config.title;
  }

  $("productPrice").textContent = config.display_price;
  $("policyText").textContent = config.policy_note;

  if (config.dev_banner) {
    showDevBanner(config.dev_banner);
  }

  setButtonState("starsButton", {
    enabled: config.stars_enabled,
    label: config.stars_enabled ? "Оплатить в Telegram" : "Stars недоступны",
    primary: true,
  });

  setButtonState("cardButton", {
    enabled: config.card_enabled,
    label: config.card_enabled ? "Оплатить картой" : "Скоро",
  });

  setButtonState("cryptoButton", {
    enabled: config.crypto_enabled,
    label: config.crypto_enabled ? "Оплатить криптой" : "Скоро",
  });
}

async function loadConfig() {
  const response = await fetch("/miniapp/api/config");
  if (!response.ok) {
    throw new Error("Не удалось загрузить настройки Mini App");
  }

  return response.json();
}

async function init() {
  try {
    state.isTelegramContext = Boolean(tg?.initData);
    tg?.ready();
    tg?.expand();
    tg?.setHeaderColor?.("#000000");
    tg?.setBackgroundColor?.("#000000");

    bindActions();
    const config = await loadConfig();
    renderConfig(config);
  } catch (error) {
    showToast(error.message);
  }
}

init();
