"use strict";
const ui =
  document.documentElement.lang === "ar"
    ? {
        area: "اختر منطقتك",
        unknown: "يُحدّد لاحقاً",
        preparing: "جارٍ تجهيز طلبك…",
        bagError: "تعذّر تحديث السلة. حاول مرة أخرى.",
        openBag: "افتح السلة ←",
      }
    : {
        area: "Choose your area",
        unknown: "To be confirmed",
        preparing: "Preparing your order…",
        bagError: "Could not update your bag. Please try again.",
        openBag: "Open your bag →",
      };
const menu = document.querySelector(".menu-toggle");
menu?.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open));
  document.getElementById("navigation")?.classList.toggle("open", open);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    menu?.setAttribute("aria-expanded", "false");
    document.getElementById("navigation")?.classList.remove("open");
  }
});
const form = document.getElementById("product-form");
function price() {
  if (!form) return;
  const selected = form.querySelector("[name=variant]").selectedOptions[0];
  const output = document.getElementById("product-total");
  if (!selected?.value) return;
  let amount = Number(selected.dataset.price);
  form
    .querySelectorAll("[name=addon]:checked")
    .forEach((a) => (amount += Number(a.dataset.price)));
  amount *= Math.max(1, Number(form.querySelector("[name=qty]").value) || 1);
  output.textContent =
    output.dataset.currency + " " + (amount / 100).toFixed(2);
}
form?.addEventListener("input", price);
form?.addEventListener("change", price);
form?.querySelectorAll("[name=addon]").forEach((option) =>
  option.addEventListener("change", () => {
    if (option.checked && option.dataset.group)
      form.querySelectorAll("[name=addon]").forEach((other) => {
        if (other !== option && other.dataset.group === option.dataset.group)
          other.checked = false;
      });
    price();
  }),
);
form?.querySelector("[name=variant]")?.addEventListener("change", () => {
  const selected = form.querySelector("[name=variant]").selectedOptions[0];
  [
    ["grind", "grinds"],
    ["temperature", "temperatures"],
  ].forEach(([field, key]) => {
    const input = form.querySelector(`[name=${field}]`);
    if (!input) return;
    const allowed = selected.dataset[key]?.split(",").filter(Boolean) || [];
    [...input.options].forEach(
      (option) =>
        (option.disabled =
          allowed.length > 0 && !allowed.includes(option.value)),
    );
    if (input.selectedOptions[0]?.disabled)
      input.value =
        [...input.options].find((option) => !option.disabled)?.value || "";
  });
});
document.querySelectorAll("[data-quantity]").forEach((button) =>
  button.addEventListener("click", () => {
    const input = button.closest(".quantity-control").querySelector("input");
    const min = Number(input.min || 1),
      max = Number(input.max || 99);
    input.value = String(
      Math.max(
        min,
        Math.min(
          max,
          (Number(input.value) || 1) + Number(button.dataset.quantity),
        ),
      ),
    );
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }),
);
document.querySelectorAll(".gallery-thumb").forEach((button) =>
  button.addEventListener("click", () => {
    const image = document.getElementById("main-product-image");
    if (image) image.src = button.dataset.src;
    document
      .querySelectorAll(".gallery-thumb")
      .forEach((other) => other.classList.toggle("selected", other === button));
  }),
);
const area = document.getElementById("delivery-area");
function deliveryTotal() {
  if (!area) return;
  const value = area.selectedOptions[0]?.dataset.fee;
  const fee = document.getElementById("delivery-fee"),
    total = document.getElementById("checkout-total");
  if (!value) {
    fee.textContent = ui.area;
    total.textContent = "—";
  } else if (value === "unknown") {
    fee.textContent = ui.unknown;
    total.textContent = ui.unknown;
  } else {
    fee.textContent =
      total.dataset.currency + " " + (Number(value) / 100).toFixed(2);
    total.textContent =
      total.dataset.currency +
      " " +
      ((Number(total.dataset.subtotal) + Number(value)) / 100).toFixed(2);
  }
}
area?.addEventListener("change", deliveryTotal);
deliveryTotal();
document.querySelectorAll("form[data-submit-once]").forEach((f) =>
  f.addEventListener("submit", () => {
    const button = f.querySelector("button");
    button.disabled = true;
    button.textContent = ui.preparing;
  }),
);
document.querySelectorAll("form[data-confirm]").forEach((f) =>
  f.addEventListener("submit", (e) => {
    if (!confirm(f.dataset.confirm)) e.preventDefault();
  }),
);
const drawer = document.getElementById("cart-drawer"),
  drawerBody = document.getElementById("drawer-body"),
  drawerStatus = document.getElementById("drawer-status");
function renderBag(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const root = doc.getElementById("cart-root");
  if (!root) throw new Error("Your bag could not be loaded.");
  const pageCart = document.querySelector("main #cart-root");
  if (pageCart) pageCart.replaceWith(root.cloneNode(true));
  root.id = "drawer-cart-root";
  const summary = root.querySelector(".cart-summary");
  const footer = document.getElementById("drawer-footer");
  footer.replaceChildren();
  if (summary) {
    const total = summary.querySelector(".cart-total");
    const delivery = summary.querySelector(".summary-line");
    const checkout = summary.querySelector('a[href="/checkout"]');
    if (total) footer.append(total);
    if (delivery) footer.append(delivery);
    if (checkout) footer.append(checkout);
    summary.remove();
  }
  drawerBody.replaceChildren(root);
  document
    .querySelectorAll("[data-cart-count]")
    .forEach((count) => (count.textContent = root.dataset.count || "0"));
  drawerStatus.textContent = [...doc.querySelectorAll(".flash")]
    .map((message) => message.textContent.trim())
    .join(" ");
}
async function openBag() {
  if (!drawer?.showModal) {
    location.href = "/cart";
    return;
  }
  if (!drawer.open) drawer.showModal();
  drawerStatus.textContent = "";
  drawer.setAttribute("aria-busy", "true");
  try {
    const response = await fetch("/cart", { credentials: "same-origin" });
    if (!response.ok) throw new Error();
    renderBag(await response.text());
    drawerBody.scrollTop = 0;
  } catch {
    document.getElementById("drawer-footer").replaceChildren();
    drawerBody.textContent =
      "Your bag could not be loaded. Please open the bag page to continue.";
    const link = document.createElement("a");
    link.href = "/cart";
    link.textContent = ui.openBag;
    link.className = "button dark";
    drawerBody.append(link);
  } finally {
    drawer.removeAttribute("aria-busy");
  }
}
document.querySelectorAll("[data-cart-open]").forEach((link) =>
  link.addEventListener("click", (e) => {
    if (!drawer?.showModal) return;
    e.preventDefault();
    openBag();
  }),
);
document
  .querySelector("[data-close-cart]")
  ?.addEventListener("click", () => drawer.close());
drawer?.addEventListener("click", (e) => {
  if (e.target === drawer) drawer.close();
});
drawer?.addEventListener("submit", async (e) => {
  const f = e.target;
  if (!f.matches('form[action="/cart"]')) return;
  e.preventDefault();
  const data = new FormData(f);
  if (e.submitter?.name) data.set(e.submitter.name, e.submitter.value);
  drawer.setAttribute("aria-busy", "true");
  try {
    const response = await fetch("/cart", {
      method: "POST",
      body: data,
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error();
    renderBag(await response.text());
  } catch {
    drawerStatus.textContent =
      "Could not update your bag. Please try again or open the bag page.";
  } finally {
    drawer.removeAttribute("aria-busy");
  }
});
form?.addEventListener("submit", async (e) => {
  if (!drawer?.showModal || !window.fetch) return;
  e.preventDefault();
  if (form.getAttribute("aria-busy") === "true") return;
  const button = form.querySelector("button[type=submit],.purchase-row button");
  button.disabled = true;
  form.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error();
    renderBag(await response.text());
    if (!drawer.open) drawer.showModal();
  } catch {
    const toast = document.getElementById("toast");
    toast.hidden = false;
    toast.textContent = ui.bagError;
    setTimeout(() => (toast.hidden = true), 5000);
  } finally {
    button.disabled = false;
    form.removeAttribute("aria-busy");
  }
});
// Only public product IDs are stored, never names, prices or customer details.
try {
  const current =
    document.querySelector("[data-product-id]")?.dataset.productId;
  let ids = JSON.parse(localStorage.getItem("lux.recentProducts") || "[]");
  if (!Array.isArray(ids)) ids = [];
  ids = ids
    .filter((id) => /^\d+$/.test(String(id)))
    .map(String)
    .slice(0, 6);
  if (current) {
    ids = [
      String(current),
      ...ids.filter((id) => id !== String(current)),
    ].slice(0, 6);
    localStorage.setItem("lux.recentProducts", JSON.stringify(ids));
  }
  const section = document.getElementById("recently-viewed");
  if (section && ids.length) {
    fetch("/recently-viewed?ids=" + encodeURIComponent(ids.join(",")), {
      credentials: "same-origin",
    })
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.text();
      })
      .then((html) => {
        const doc = new DOMParser().parseFromString(html, "text/html");
        const cards = doc.querySelector(".product-grid");
        if (cards) {
          document.getElementById("recently-products").replaceChildren(cards);
          section.hidden = false;
        }
      })
      .catch(() => {});
  }
} catch {
  /* Browsing works when storage is unavailable. */
}
function finderOptions() {
  const kind = document.querySelector(
    ".finder-choices [name=kind]:checked",
  )?.value;
  document
    .querySelectorAll("[data-finder-kind]")
    .forEach((panel) => (panel.hidden = panel.dataset.finderKind !== kind));
}
document
  .querySelectorAll(".finder-choices [name=kind]")
  .forEach((input) => input.addEventListener("change", finderOptions));
finderOptions();
if (
  !matchMedia("(prefers-reduced-motion: reduce)").matches &&
  "IntersectionObserver" in window
) {
  const observer = new IntersectionObserver(
    (entries) =>
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      }),
    { threshold: 0.03 },
  );
  document.querySelectorAll(".reveal").forEach((element) => {
    element.classList.add("will-reveal");
    observer.observe(element);
  });
}

const checkoutSelection = document.querySelector(".checkout-selection");
if (checkoutSelection && matchMedia("(max-width:620px)").matches)
  checkoutSelection.open = false;
