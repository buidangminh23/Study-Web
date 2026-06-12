(() => {
    const STORAGE_KEY = 'PAGE_AGENT_API_KEY'

    function getApiKey() {
        return localStorage.getItem(STORAGE_KEY) || ''
    }

    function initAgent() {
        const apiKey = getApiKey()
        if (!apiKey) return
        if (typeof PageAgent !== 'function') {
            console.warn('[PageAgent] Library is not loaded.')
            return
        }

        window.__pageAgent = new PageAgent({
            model: 'gemini-2.0-flash',
            baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai/',
            apiKey,
        })
    }

    window.setPageAgentKey = (key) => {
        localStorage.setItem(STORAGE_KEY, key)
        initAgent()
        console.log('[PageAgent] API key saved and agent initialized.')
    }

    window.runPageAgent = async (task) => {
        if (!window.__pageAgent) {
            console.warn('[PageAgent] Not initialized. Run: setPageAgentKey("your-key")')
            return
        }
        return window.__pageAgent.execute(task)
    }

    initAgent()
})()
