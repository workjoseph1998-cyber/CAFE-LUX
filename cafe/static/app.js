"use strict";
const menu = document.querySelector(".menu-toggle");
menu?.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open));
  document.getElementById("navigation").classList.toggle("open", open);
});
const form = document.getElementById("product-form");
function price() {
  if (!form) return;
  const v = form.querySelector("[name=variant]").selectedOptions[0];
  const out = document.getElementById("product-total");
  if (!v?.value) return;
  let cents = Number(v.dataset.price);
  form
    .querySelectorAll("[name=addon]:checked")
    .forEach((a) => (cents += Number(a.dataset.price)));
  cents *= Math.max(1, Number(form.querySelector("[name=qty]").value) || 1);
  out.textContent = out.dataset.currency + " " + (cents / 100).toFixed(2);
}
form?.addEventListener("change", price);
form?.addEventListener("input", price);
const fulfillment = document.getElementById("fulfillment");
function checkoutTotal() {
  if (!fulfillment) return;
  const fee = Number(fulfillment.selectedOptions[0]?.dataset.fee || 0);
  const total = document.getElementById("checkout-total");
  document.getElementById("delivery-fee").textContent = fee.toFixed(2);
  total.textContent =
    total.dataset.currency +
    " " +
    (Number(total.dataset.subtotal) / 100 + fee).toFixed(2);
  document.querySelector("[name=address]").required =
    fulfillment.value === "delivery";
}
fulfillment?.addEventListener("change", checkoutTotal);
checkoutTotal();
document.querySelectorAll(".gallery-thumb").forEach((b) =>
  b.addEventListener("click", () => {
    const img = document.getElementById("main-product-image");
    if (img) img.src = b.dataset.src;
  }),
);
document.querySelectorAll("form[data-confirm]").forEach((f) =>
  f.addEventListener("submit", (e) => {
    if (!confirm(f.dataset.confirm)) e.preventDefault();
  }),
);
const upload = document.querySelector("[name=upload]");
let previewUrl;
upload?.addEventListener("change", () => {
  const preview = document.querySelector(".upload-preview");
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  if (upload.files[0]) {
    previewUrl = URL.createObjectURL(upload.files[0]);
    preview.src = previewUrl;
    preview.hidden = false;
  }
});
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!reduce && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) =>
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("visible");
          observer.unobserve(e.target);
        }
      }),
    { threshold: 0.08 },
  );
  document.querySelectorAll(".reveal").forEach((e) => {
    e.classList.add("will-reveal");
    observer.observe(e);
  });
}
