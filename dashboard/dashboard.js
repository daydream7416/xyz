(() => {
    const STORAGE_PREFIX = "metra-dashboard";
    const STORAGE_KEYS = {
        token: `${STORAGE_PREFIX}:session-token`,
        apiBaseUrl: `${STORAGE_PREFIX}:api-base-url`,
    };

    const elements = {
        loginView: document.getElementById("login_view"),
        loginForm: document.getElementById("login_form"),
        loginFeedback: document.getElementById("login_feedback"),
        apiBaseInput: document.getElementById("api_base_url"),
        headerSubtitle: document.getElementById("header_subtitle"),
        dashboardView: document.getElementById("dashboard_view"),
        dashboardStatus: document.getElementById("dashboard_status"),
        lastSync: document.getElementById("last_sync_time"),
        currentUserName: document.getElementById("current_user_name"),
        currentUserEmail: document.getElementById("current_user_email"),
        currentApiBase: document.getElementById("current_api_base"),
        logoutButton: document.getElementById("logout_button"),
        propertyForm: document.getElementById("property_form"),
        propertyFormTitle: document.getElementById("property_form_title"),
        propertyFormFeedback: document.getElementById("property_form_feedback"),
        propertySubmitButton: document.getElementById("property_submit_button"),
        resetFormButton: document.getElementById("reset_form_button"),
        propertiesTableBody: document.getElementById("properties_table_body"),
        propertiesEmptyState: document.getElementById("properties_empty"),
        propertyRowTemplate: document.getElementById("property_row_template"),
        filterStatus: document.getElementById("filter_status"),
    };

    const propertyInputs = {
        id: document.getElementById("property_id"),
        title: document.getElementById("prop_title"),
        status: document.getElementById("prop_status"),
        category: document.getElementById("prop_category"),
        price: document.getElementById("prop_price"),
        location: document.getElementById("prop_location"),
        description: document.getElementById("prop_description"),
        tagline: document.getElementById("prop_tagline"),
        imageUrl: document.getElementById("prop_image_url"),
        area: document.getElementById("prop_area"),
        rooms: document.getElementById("prop_rooms"),
        zoningStatus: document.getElementById("prop_zoning"),
        floor: document.getElementById("prop_floor"),
        buildingAge: document.getElementById("prop_building_age"),
        specs: document.getElementById("prop_specs"),
        featured: document.getElementById("prop_featured"),
    };

    const state = {
        token: null,
        apiBaseUrl: null,
        user: null,
        properties: [],
        isSubmitting: false,
    };

    function init() {
        state.apiBaseUrl = loadStoredApiBaseUrl() || getDefaultApiBaseUrl();
        if (elements.apiBaseInput) {
            elements.apiBaseInput.value = state.apiBaseUrl;
        }

        const storedToken = loadStoredToken();
        if (storedToken) {
            state.token = storedToken;
            bootstrapAuthenticatedSession().catch((error) => {
                console.error("Bootstrap error", error);
                hardLogout("Oturum doğrulanamadı, lütfen tekrar giriş yapın.");
            });
        } else {
            toggleView("login");
        }

        bindEventListeners();
    }

    function bindEventListeners() {
        if (elements.loginForm) {
            elements.loginForm.addEventListener("submit", handleLoginSubmit);
        }
        if (elements.logoutButton) {
            elements.logoutButton.addEventListener("click", () => {
                hardLogout("Çıkış yapıldı.");
            });
        }
        if (elements.propertyForm) {
            elements.propertyForm.addEventListener("submit", handlePropertySubmit);
        }
        if (elements.resetFormButton) {
            elements.resetFormButton.addEventListener("click", (event) => {
                event.preventDefault();
                resetPropertyForm();
            });
        }
        if (elements.propertiesTableBody) {
            elements.propertiesTableBody.addEventListener("click", handleTableAction);
        }
        if (elements.filterStatus) {
            elements.filterStatus.addEventListener("change", () => {
                renderProperties();
            });
        }
    }

    async function bootstrapAuthenticatedSession() {
        toggleView("loading");
        try {
            await fetchCurrentUser();
            await refreshProperties();
            toggleView("dashboard");
            setDashboardStatus("Hoş geldiniz! Portföyünüz başarıyla yüklendi.", "success");
        } catch (error) {
            console.error("Session bootstrap failed", error);
            hardLogout("Oturum doğrulaması başarısız oldu. Lütfen tekrar giriş yapın.");
        }
    }

    function toggleView(mode) {
        const showDashboard = mode === "dashboard";
        const showLogin = mode === "login";
        if (elements.loginView) {
            elements.loginView.classList.toggle("hidden", !showLogin);
        }
        if (elements.dashboardView) {
            elements.dashboardView.classList.toggle("hidden", !showDashboard);
        }

        if (elements.logoutButton) {
            elements.logoutButton.classList.toggle("hidden", !showDashboard);
        }

        if (mode === "loading") {
            setDashboardStatus("Oturum doğrulanıyor…", "info");
        }
    }

    function getDefaultApiBaseUrl() {
        const host = window.location.hostname || "";
        if (host === "localhost" || host === "127.0.0.1") {
            return "http://localhost:8000";
        }
        if (host.endsWith(".vercel.app")) {
            return "https://metra-ai-monorepo-production.up.railway.app";
        }
        if (host.endsWith("metraai.xyz")) {
            return "https://metra-ai-monorepo-production.up.railway.app";
        }
        if (host.endsWith("metraap.com")) {
            return "https://metra-ai-monorepo-production.up.railway.app";
        }
        return "https://metra-ai-monorepo-production.up.railway.app";
    }

    function loadStoredToken() {
        try {
            return localStorage.getItem(STORAGE_KEYS.token);
        } catch {
            return null;
        }
    }

    function persistToken(token) {
        state.token = token;
        try {
            if (token) {
                localStorage.setItem(STORAGE_KEYS.token, token);
            } else {
                localStorage.removeItem(STORAGE_KEYS.token);
            }
        } catch (error) {
            console.warn("Oturum anahtarı saklanamadı:", error);
        }
    }

    function loadStoredApiBaseUrl() {
        try {
            return localStorage.getItem(STORAGE_KEYS.apiBaseUrl);
        } catch {
            return null;
        }
    }

    function persistApiBaseUrl(url) {
        state.apiBaseUrl = url;
        try {
            if (url) {
                localStorage.setItem(STORAGE_KEYS.apiBaseUrl, url);
            } else {
                localStorage.removeItem(STORAGE_KEYS.apiBaseUrl);
            }
        } catch (error) {
            console.warn("API adresi saklanamadı:", error);
        }
    }

    function setDashboardStatus(message, tone = "info") {
        if (!elements.dashboardStatus) {
            return;
        }
        elements.dashboardStatus.textContent = message;
        const toneClasses = {
            info: "text-slate-300",
            success: "text-emerald-300",
            warning: "text-amber-300",
            error: "text-rose-300",
        };
        Object.values(toneClasses).forEach((cls) => elements.dashboardStatus.classList.remove(cls));
        elements.dashboardStatus.classList.add(toneClasses[tone] || toneClasses.info);
    }

    function updateLastSync(timestamp = new Date()) {
        if (!elements.lastSync) {
            return;
        }
        const formatted = timestamp.toLocaleString("tr-TR", {
            dateStyle: "short",
            timeStyle: "short",
        });
        elements.lastSync.textContent = `Son güncelleme: ${formatted}`;
    }

    async function handleLoginSubmit(event) {
        event.preventDefault();
        if (!elements.loginForm) return;

        const formData = new FormData(elements.loginForm);
        const email = String(formData.get("email") || "").trim();
        const password = String(formData.get("password") || "").trim();
        let apiBaseUrl = String(formData.get("api_base_url") || "").trim();

        if (!email || !password || !apiBaseUrl) {
            setLoginFeedback("Lütfen tüm alanları doldurun.");
            return;
        }

        apiBaseUrl = normalizeBaseUrl(apiBaseUrl);
        persistApiBaseUrl(apiBaseUrl);
        if (elements.apiBaseInput) {
            elements.apiBaseInput.value = apiBaseUrl;
        }

        try {
            setLoginFeedback("Giriş yapılıyor…", "info");
            const token = await performLogin(apiBaseUrl, email, password);
            persistToken(token);
            elements.loginForm.reset();
            setLoginFeedback("");
            await bootstrapAuthenticatedSession();
        } catch (error) {
            console.error("Login failed", error);
            setLoginFeedback(error.message || "Giriş başarısız. Bilgilerinizi kontrol edin.", "error");
        }
    }

    function normalizeBaseUrl(url) {
        if (!url) return "";
        try {
            const parsed = new URL(url);
            return `${parsed.protocol}//${parsed.host}`;
        } catch {
            return url.replace(/\/+$/, "");
        }
    }

    function setLoginFeedback(message, tone = "error") {
        if (!elements.loginFeedback) return;
        elements.loginFeedback.textContent = message;
        const toneClasses = {
            info: "text-slate-300",
            error: "text-rose-400",
        };
        Object.values(toneClasses).forEach((cls) => elements.loginFeedback.classList.remove(cls));
        if (message) {
            elements.loginFeedback.classList.add(toneClasses[tone] || toneClasses.error);
        }
    }

    async function performLogin(apiBaseUrl, email, password) {
        const loginUrl = `${apiBaseUrl.replace(/\/$/, "")}/auth/login`;
        const payload = new URLSearchParams({ email, password });

        const response = await fetch(loginUrl, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: payload.toString(),
        });
        if (!response.ok) {
            const detail = await safeReadJson(response);
            const message = detail?.detail || "Giriş yapılamadı.";
            throw new Error(message);
        }
        const data = await response.json();
        if (!data?.access_token) {
            throw new Error("Beklenmeyen yanıt: access_token bulunamadı.");
        }
        persistApiBaseUrl(apiBaseUrl);
        return data.access_token;
    }

    async function fetchCurrentUser() {
        const data = await apiRequest("/auth/me");
        state.user = data;
        if (elements.currentUserName) {
            elements.currentUserName.textContent = data?.name || "-";
        }
        if (elements.currentUserEmail) {
            elements.currentUserEmail.textContent = data?.email || "-";
        }
        if (elements.currentApiBase) {
            elements.currentApiBase.textContent = state.apiBaseUrl || "-";
        }
        if (elements.headerSubtitle) {
            elements.headerSubtitle.textContent = "Premium oturum aktif";
        }
    }

    async function refreshProperties() {
        const records = await apiRequest("/properties/?only_mine=true");
        state.properties = Array.isArray(records) ? records : [];
        renderProperties();
        updateLastSync();
    }

    function renderProperties() {
        if (!elements.propertiesTableBody) return;

        const statusFilter = (elements.filterStatus?.value || "").trim().toLowerCase();
        const filtered = state.properties.filter((item) => {
            if (!statusFilter) {
                return true;
            }
            return (item.status || "").toLowerCase() === statusFilter;
        });

        elements.propertiesTableBody.innerHTML = "";

        if (!filtered.length) {
            if (elements.propertiesEmptyState) {
                elements.propertiesEmptyState.classList.remove("hidden");
            }
            return;
        }

        if (elements.propertiesEmptyState) {
            elements.propertiesEmptyState.classList.add("hidden");
        }

        filtered.forEach((property) => {
            const row = cloneRowTemplate();
            if (!row) return;
            const [titleCell, statusCell, categoryCell, priceCell, specsCell] = row.querySelectorAll("td");
            if (titleCell) {
                titleCell.textContent = property.title || "-";
            }
            if (statusCell) {
                statusCell.textContent = capitalize(property.status || "satılık");
            }
            if (categoryCell) {
                categoryCell.textContent = (property.category || "-").toUpperCase();
            }
            if (priceCell) {
                priceCell.textContent = property.price || "-";
            }
            if (specsCell) {
                const specs = Array.isArray(property.specs) ? property.specs : [];
                if (specs.length) {
                    specsCell.innerHTML = specs
                        .map((spec) => `<span class="mr-1 inline-flex items-center rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200">${escapeHtml(spec)}</span>`)
                        .join("");
                } else {
                    specsCell.textContent = "—";
                }
            }
            row.dataset.propertyId = String(property.id);
            elements.propertiesTableBody.appendChild(row);
        });
    }

    function cloneRowTemplate() {
        if (!elements.propertyRowTemplate?.content) return null;
        return elements.propertyRowTemplate.content.firstElementChild.cloneNode(true);
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function capitalize(value) {
        if (!value) return "";
        const lower = value.toString().toLowerCase();
        return lower.charAt(0).toUpperCase() + lower.slice(1);
    }

    async function apiRequest(endpoint, options = {}) {
        if (!state.apiBaseUrl) {
            throw new Error("API adresi ayarlı değil.");
        }
        const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
        const url = `${state.apiBaseUrl.replace(/\/$/, "")}${normalizedEndpoint}`;
        const headers = new Headers(options.headers || {});
        headers.set("Accept", "application/json");
        if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.method && options.method !== "GET") {
            headers.set("Content-Type", "application/json");
        }
        if (state.token) {
            headers.set("X-Session-Token", state.token);
        }

        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            hardLogout("Oturum süreniz doldu. Lütfen tekrar giriş yapın.");
            throw new Error("Yetkilendirme başarısız.");
        }
        if (response.status === 403) {
            throw new Error("Bu işlem için yetkiniz bulunmuyor.");
        }
        if (!response.ok) {
            const detail = await safeReadJson(response);
            const message = detail?.detail || "İstek başarısız oldu.";
            throw new Error(message);
        }
        if (response.status === 204) {
            return null;
        }
        return response.json();
    }

    async function safeReadJson(response) {
        try {
            return await response.json();
        } catch {
            return null;
        }
    }

    async function handlePropertySubmit(event) {
        event.preventDefault();
        if (state.isSubmitting) return;

        const payload = buildPropertyPayloadFromForm();
        if (!payload) {
            setPropertyFormFeedback("Lütfen zorunlu alanları doldurun.");
            return;
        }

        const propertyId = propertyInputs.id?.value?.trim();
        state.isSubmitting = true;
        setPropertyFormFeedback(propertyId ? "İlan güncelleniyor…" : "İlan ekleniyor…", "info");
        elements.propertySubmitButton?.setAttribute("disabled", "disabled");

        try {
            if (propertyId) {
                await apiRequest(`/properties/${propertyId}`, {
                    method: "PUT",
                    body: JSON.stringify(payload),
                });
                setPropertyFormFeedback("İlan başarıyla güncellendi.", "success");
            } else {
                await apiRequest("/properties/", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                setPropertyFormFeedback("İlan başarıyla eklendi.", "success");
            }
            await refreshProperties();
            resetPropertyForm(false);
        } catch (error) {
            console.error("Property submit failed", error);
            setPropertyFormFeedback(error.message || "İlan kaydedilemedi.", "error");
        } finally {
            state.isSubmitting = false;
            elements.propertySubmitButton?.removeAttribute("disabled");
        }
    }

    function buildPropertyPayloadFromForm() {
        const title = propertyInputs.title?.value?.trim();
        if (!title) return null;

        const status = propertyInputs.status?.value?.trim().toLowerCase() || "satılık";
        const category = propertyInputs.category?.value?.trim().toLowerCase() || "arsa";

        const specsRaw = propertyInputs.specs?.value || "";
        const specs = specsRaw
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);

        const payload = {
            title,
            status,
            category,
            price: optionalValue(propertyInputs.price?.value),
            location: optionalValue(propertyInputs.location?.value),
            description: optionalValue(propertyInputs.description?.value),
            tagline: optionalValue(propertyInputs.tagline?.value),
            image_url: optionalValue(propertyInputs.imageUrl?.value),
            area: optionalValue(propertyInputs.area?.value),
            rooms: optionalValue(propertyInputs.rooms?.value),
            zoning_status: optionalValue(propertyInputs.zoningStatus?.value),
            floor: optionalValue(propertyInputs.floor?.value),
            building_age: optionalValue(propertyInputs.buildingAge?.value),
            featured: Boolean(propertyInputs.featured?.checked),
            specs,
        };
        return payload;
    }

    function optionalValue(value) {
        if (typeof value === "string") {
            const trimmed = value.trim();
            return trimmed.length ? trimmed : null;
        }
        return value ?? null;
    }

    function setPropertyFormFeedback(message, tone = "error") {
        if (!elements.propertyFormFeedback) return;
        elements.propertyFormFeedback.textContent = message || "";
        const toneClasses = {
            info: "text-slate-300",
            success: "text-emerald-300",
            error: "text-rose-400",
        };
        Object.values(toneClasses).forEach((cls) => elements.propertyFormFeedback.classList.remove(cls));
        if (message) {
            elements.propertyFormFeedback.classList.add(toneClasses[tone] || toneClasses.error);
        }
    }

    function resetPropertyForm(clearFeedback = true) {
        propertyInputs.id.value = "";
        propertyInputs.title.value = "";
        propertyInputs.status.value = "satılık";
        propertyInputs.category.value = "arsa";
        propertyInputs.price.value = "";
        propertyInputs.location.value = "";
        propertyInputs.description.value = "";
        propertyInputs.tagline.value = "";
        propertyInputs.imageUrl.value = "";
        propertyInputs.area.value = "";
        propertyInputs.rooms.value = "";
        propertyInputs.zoningStatus.value = "";
        propertyInputs.floor.value = "";
        propertyInputs.buildingAge.value = "";
        propertyInputs.specs.value = "";
        propertyInputs.featured.checked = false;

        if (elements.propertyFormTitle) {
            elements.propertyFormTitle.textContent = "Yeni ilan ekle";
        }
        if (elements.resetFormButton) {
            elements.resetFormButton.classList.add("hidden");
        }
        if (elements.propertySubmitButton) {
            elements.propertySubmitButton.textContent = "İlanı kaydet";
        }
        if (clearFeedback) {
            setPropertyFormFeedback("");
        }
    }

    function populateFormForEdit(propertyId) {
        const record = state.properties.find((item) => String(item.id) === String(propertyId));
        if (!record) {
            setDashboardStatus("Seçilen ilan bulunamadı.", "warning");
            return;
        }

        propertyInputs.id.value = record.id;
        propertyInputs.title.value = record.title || "";
        propertyInputs.status.value = (record.status || "satılık").toLowerCase();
        propertyInputs.category.value = (record.category || "arsa").toLowerCase();
        propertyInputs.price.value = record.price || "";
        propertyInputs.location.value = record.location || "";
        propertyInputs.description.value = record.description || "";
        propertyInputs.tagline.value = record.tagline || "";
        propertyInputs.imageUrl.value = record.image_url || "";
        propertyInputs.area.value = record.area || "";
        propertyInputs.rooms.value = record.rooms || "";
        propertyInputs.zoningStatus.value = record.zoning_status || "";
        propertyInputs.floor.value = record.floor || "";
        propertyInputs.buildingAge.value = record.building_age || "";
        propertyInputs.specs.value = Array.isArray(record.specs) ? record.specs.join(", ") : "";
        propertyInputs.featured.checked = Boolean(record.featured);

        if (elements.propertyFormTitle) {
            elements.propertyFormTitle.textContent = "İlanı düzenle";
        }
        if (elements.resetFormButton) {
            elements.resetFormButton.classList.remove("hidden");
        }
        if (elements.propertySubmitButton) {
            elements.propertySubmitButton.textContent = "İlanı güncelle";
        }
        setPropertyFormFeedback("Seçilen ilan form alanlarına yüklendi.", "info");
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    async function deleteProperty(propertyId) {
        if (!propertyId) return;
        const confirmed = window.confirm("Bu ilanı silmek istediğinizden emin misiniz?");
        if (!confirmed) return;

        try {
            await apiRequest(`/properties/${propertyId}`, { method: "DELETE" });
            setDashboardStatus("İlan silindi.", "success");
            await refreshProperties();
            if (propertyInputs.id.value === String(propertyId)) {
                resetPropertyForm();
            }
        } catch (error) {
            console.error("Delete failed", error);
            setDashboardStatus(error.message || "İlan silinemedi.", "error");
        }
    }

    function handleTableAction(event) {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const action = target.dataset.action;
        if (!action) return;

        const row = target.closest("tr");
        if (!row || !row.dataset.propertyId) return;
        const propertyId = row.dataset.propertyId;

        if (action === "edit") {
            populateFormForEdit(propertyId);
        } else if (action === "delete") {
            deleteProperty(propertyId);
        }
    }

    function hardLogout(message) {
        persistToken(null);
        state.user = null;
        state.properties = [];
        renderProperties();
        resetPropertyForm();
        toggleView("login");
        if (elements.headerSubtitle) {
            elements.headerSubtitle.textContent = "Premium danışmanlar için yönetim ekranı";
        }
        if (message) {
            setLoginFeedback(message, "info");
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
