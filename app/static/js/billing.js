// ============================================================================
// BILLING PAGE — LIVE CART LOGIC
// ----------------------------------------------------------------------------
// This is the only "heavy" JavaScript in the whole project. Everything here
// runs entirely in the browser — the cart itself only exists in memory
// (the `cart` object below) until "Generate Bill" is clicked, at which
// point it's sent to the server as JSON and Flask re-validates everything
// from the database (see billing.py) — the browser is never trusted for
// the final prices/stock check, only for a nice live-updating display.
//
// The (function () { ... })() wrapper around this whole file is called an
// IIFE (Immediately Invoked Function Expression) — it runs itself once,
// immediately. Its only real purpose here is to keep every variable below
// (cart, searchTimer, etc.) private to this file, so it can't accidentally
// clash with a same-named variable in some other script on the page.
// ============================================================================
(function () {
    // Grab references to all the HTML elements this script needs to read
    // from or write to. document.getElementById() finds an element by its
    // id="..." attribute in the HTML.
    const searchInput = document.getElementById("productSearch");
    const resultsBox = document.getElementById("searchResults");
    const cartBody = document.getElementById("cartBody");
    const emptyCartRow = document.getElementById("emptyCartRow");
    const cartDataInput = document.getElementById("cartDataInput");
    const generateBillBtn = document.getElementById("generateBillBtn");
    const discountInput = document.getElementById("discountInput");
    const taxInput = document.getElementById("taxInput");

    const subtotalDisplay = document.getElementById("subtotalDisplay");
    const discountDisplay = document.getElementById("discountDisplay");
    const taxDisplay = document.getElementById("taxDisplay");
    const totalDisplay = document.getElementById("totalDisplay");

    // cart: { productId: { id, name, price, stock, unit, qty } }
    // This is a plain JavaScript object being used like a dictionary/map —
    // the KEYS are variant ids, and each VALUE is everything we need to
    // display and total that cart line. Using an object (not an array)
    // means "does this item already exist in the cart?" is a fast, simple
    // check: `if (cart[id])`.
    const cart = {};
    let searchTimer = null;

    function formatINR(value) {
        // toLocaleString with "en-IN" gives Indian-style number grouping
        // (e.g. 1,00,000 instead of 100,000) plus exactly 2 decimal places.
        return "₹" + value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // "Debouncing": every time the cashier types a letter, this event fires.
    // If we searched on every single keystroke, that's a network request
    // per letter — wasteful and can feel laggy. Instead, clearTimeout()
    // cancels any pending search, and we only actually search 200ms AFTER
    // the person stops typing. This is a very common real-world pattern
    // for any live search box.
    searchInput.addEventListener("input", function () {
        const q = this.value.trim();
        clearTimeout(searchTimer);
        if (!q) {
            resultsBox.innerHTML = "";
            return;
        }
        searchTimer = setTimeout(() => runSearch(q), 200);
    });

    function runSearch(q) {
        fetch(`/inventory/api/search?q=${encodeURIComponent(q)}`)
            .then((res) => res.json())
            .then((products) => renderResults(products, q))
            .catch(() => {
                resultsBox.innerHTML = `<div class="list-group-item text-danger">Search failed. Check server connection.</div>`;
            });
    }

    function renderResults(products, query) {
        const addNewRow = `
            <div class="list-group-item d-flex justify-content-between align-items-center text-primary" id="addNewProductRow">
                <span><i class="bi bi-plus-circle"></i> Add "${escapeHtml(query)}" as new product</span>
            </div>`;

        if (products.length === 0) {
            resultsBox.innerHTML =
                `<div class="list-group-item text-muted">No matching products found.</div>` + addNewRow;
        } else {
            resultsBox.innerHTML =
                products
                    .map(
                        (p) => `
                    <div class="list-group-item d-flex justify-content-between align-items-center" data-id="${p.id}">
                        <div>
                            <div class="fw-semibold">${escapeHtml(p.display_name)}</div>
                            <div class="text-muted small">${escapeHtml(p.category)} · ${formatINR(p.price)} / ${escapeHtml(p.unit)} · Stock: ${p.stock_qty}</div>
                        </div>
                        <i class="bi bi-plus-circle text-primary fs-5"></i>
                    </div>`
                    )
                    .join("") + addNewRow;
        }

        resultsBox.querySelectorAll(".list-group-item[data-id]").forEach((el) => {
            el.addEventListener("click", () => {
                const id = el.getAttribute("data-id");
                const product = products.find((p) => String(p.id) === id);
                addToCart(product);
                searchInput.value = "";
                resultsBox.innerHTML = "";
                searchInput.focus();
            });
        });

        const addNewEl = document.getElementById("addNewProductRow");
        if (addNewEl) {
            addNewEl.addEventListener("click", () => openQuickAddModal(query));
        }
    }

    // --- Quick-add product modal ---
    const quickAddModalEl = document.getElementById("quickAddModal");
    const quickAddModal = quickAddModalEl ? new bootstrap.Modal(quickAddModalEl) : null;
    const qaName = document.getElementById("qaName");
    const qaLabel = document.getElementById("qaLabel");
    const qaCategory = document.getElementById("qaCategory");
    const qaUnit = document.getElementById("qaUnit");
    const qaPrice = document.getElementById("qaPrice");
    const qaStock = document.getElementById("qaStock");
    const qaError = document.getElementById("quickAddError");
    const qaSubmitBtn = document.getElementById("qaSubmitBtn");

    function openQuickAddModal(prefillName) {
        qaError.classList.add("d-none");
        qaName.value = prefillName || "";
        qaLabel.value = "";
        qaCategory.value = "General";
        qaUnit.value = "pcs";
        qaPrice.value = "";
        qaStock.value = "";
        quickAddModal.show();
        setTimeout(() => qaName.focus(), 300);
    }

    if (qaSubmitBtn) {
        qaSubmitBtn.addEventListener("click", () => {
            const payload = {
                name: qaName.value.trim(),
                label: qaLabel.value.trim(),
                category: qaCategory.value.trim() || "General",
                unit: qaUnit.value.trim() || "pcs",
                price: parseFloat(qaPrice.value),
                stock_qty: parseInt(qaStock.value, 10),
            };

            if (!payload.name || isNaN(payload.price) || isNaN(payload.stock_qty)) {
                qaError.textContent = "Please fill in product name, price, and stock quantity.";
                qaError.classList.remove("d-none");
                return;
            }

            fetch("/inventory/api/quick-add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then(async (res) => {
                    const body = await res.json();
                    if (res.status === 201) {
                        addToCart(body);
                        quickAddModal.hide();
                        searchInput.value = "";
                        resultsBox.innerHTML = "";
                    } else if (res.status === 409 && body.product) {
                        // Already exists — just add the existing one instead of duplicating.
                        addToCart(body.product);
                        quickAddModal.hide();
                        searchInput.value = "";
                        resultsBox.innerHTML = "";
                    } else {
                        qaError.textContent = body.error || "Could not add product. Please try again.";
                        qaError.classList.remove("d-none");
                    }
                })
                .catch(() => {
                    qaError.textContent = "Network error. Please try again.";
                    qaError.classList.remove("d-none");
                });
        });
    }

    function addToCart(product) {
        if (cart[product.id]) {
            if (cart[product.id].qty < product.stock_qty) {
                cart[product.id].qty += 1;
            }
        } else {
            cart[product.id] = {
                id: product.id,
                name: product.display_name,
                price: product.price,
                stock: product.stock_qty,
                unit: product.unit,
                qty: 1,
            };
        }
        renderCart();
    }

    function changeQty(id, delta) {
        const item = cart[id];
        if (!item) return;
        const newQty = item.qty + delta;
        if (newQty <= 0) {
            delete cart[id];
        } else if (newQty <= item.stock) {
            item.qty = newQty;
        }
        renderCart();
    }

    function removeItem(id) {
        delete cart[id];
        renderCart();
    }

    function renderCart() {
        const items = Object.values(cart);
        if (items.length === 0) {
            cartBody.innerHTML = "";
            cartBody.appendChild(emptyCartRow);
            generateBillBtn.disabled = true;
        } else {
            cartBody.innerHTML = items
                .map(
                    (item) => `
                    <tr>
                        <td>${escapeHtml(item.name)}<div class="text-muted small">${formatINR(item.price)} / ${escapeHtml(item.unit)}</div></td>
                        <td>
                            <div class="input-group input-group-sm">
                                <button class="btn btn-outline-secondary" type="button" data-action="dec" data-id="${item.id}">-</button>
                                <input type="text" class="form-control text-center" value="${item.qty}" readonly>
                                <button class="btn btn-outline-secondary" type="button" data-action="inc" data-id="${item.id}">+</button>
                            </div>
                        </td>
                        <td class="text-end">${formatINR(item.price)}</td>
                        <td class="text-end">${formatINR(item.price * item.qty)}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-danger" data-action="remove" data-id="${item.id}">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </td>
                    </tr>`
                )
                .join("");
            generateBillBtn.disabled = false;

            cartBody.querySelectorAll("[data-action='inc']").forEach((btn) =>
                btn.addEventListener("click", () => changeQty(btn.dataset.id, 1))
            );
            cartBody.querySelectorAll("[data-action='dec']").forEach((btn) =>
                btn.addEventListener("click", () => changeQty(btn.dataset.id, -1))
            );
            cartBody.querySelectorAll("[data-action='remove']").forEach((btn) =>
                btn.addEventListener("click", () => removeItem(btn.dataset.id))
            );
        }
        updateTotals();
    }

    function updateTotals() {
        const items = Object.values(cart);
        const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
        const discountPct = parseFloat(discountInput.value) || 0;
        const taxPct = parseFloat(taxInput.value) || 0;

        const discountAmt = subtotal * (discountPct / 100);
        const taxable = subtotal - discountAmt;
        const taxAmt = taxable * (taxPct / 100);
        const total = taxable + taxAmt;

        subtotalDisplay.textContent = formatINR(subtotal);
        discountDisplay.textContent = "- " + formatINR(discountAmt);
        taxDisplay.textContent = "+ " + formatINR(taxAmt);
        totalDisplay.textContent = formatINR(total);

        cartDataInput.value = JSON.stringify(
            items.map((item) => ({ product_id: item.id, quantity: item.qty }))
        );
    }

    discountInput.addEventListener("input", updateTotals);
    taxInput.addEventListener("input", updateTotals);

    document.getElementById("billForm").addEventListener("submit", function (e) {
        if (Object.keys(cart).length === 0) {
            e.preventDefault();
            alert("Please add at least one item to the cart.");
        }
    });

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }
})();
