(() => {
    let token = null;
    let checking = false;

    async function checkForChanges() {
        if (checking) {
            return;
        }
        checking = true;
        try {
            const response = await fetch(`/api/reload-token?t=${Date.now()}`, { cache: "no-store" });
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            if (token && data.token && data.token !== token) {
                window.location.reload();
                return;
            }
            token = data.token;
        } catch {
        } finally {
            checking = false;
        }
    }

    checkForChanges();
    window.setInterval(checkForChanges, 1500);
})();
