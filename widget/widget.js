(() => {
    "use strict";

    // =========================================================
    // Configuration
    // =========================================================

    const config =
        window.SAWAI_CHATBOT_CONFIG || {};

    const API_URL =
        config.apiUrl ||
        "http://127.0.0.1:8000/chat";

    const ANALYTICS_URL =
        API_URL.replace(
            /\/chat\/?$/,
            "/analytics/event"
        );

    const SESSION_STORAGE_KEY =
        "sawai_chat_session_id";


    // =========================================================
    // DOM references
    // =========================================================

    const launcher =
        document.getElementById(
            "sawai-chat-launcher"
        );

    const chatWindow =
        document.getElementById(
            "sawai-chat-window"
        );

    const closeButton =
        document.getElementById(
            "sawai-chat-close"
        );

    const resetButton =
        document.getElementById(
            "sawai-chat-reset"
        );

    const messages =
        document.getElementById(
            "sawai-chat-messages"
        );

    const options =
        document.getElementById(
            "sawai-chat-options"
        );

    const progress =
        document.getElementById(
            "sawai-chat-progress"
        );

    const summary =
        document.getElementById(
            "sawai-chat-summary"
        );

    const actions =
        document.getElementById(
            "sawai-chat-actions"
        );

    const form =
        document.getElementById(
            "sawai-chat-form"
        );

    const input =
        document.getElementById(
            "sawai-chat-input"
        );

    const sendButton =
        document.getElementById(
            "sawai-chat-send"
        );

    const typingIndicator =
        document.getElementById(
            "sawai-chat-typing"
        );


    // =========================================================
    // State
    // =========================================================

    let sessionId =
        localStorage.getItem(
            SESSION_STORAGE_KEY
        );

    let hasShownWelcome = false;

    let requestInProgress = false;


    // =========================================================
    // Chat window controls
    // =========================================================

    function openChat() {
        chatWindow.classList.add("open");

        chatWindow.setAttribute(
            "aria-hidden",
            "false"
        );

        launcher.setAttribute(
            "aria-expanded",
            "true"
        );

        trackAnalytics(
            "chatbot_open"
        );

        if (!hasShownWelcome) {
            showWelcomeMessage();

            hasShownWelcome = true;
        }

        setTimeout(() => {
            input.focus();
        }, 100);
    }


    function closeChat() {
        chatWindow.classList.remove("open");

        chatWindow.setAttribute(
            "aria-hidden",
            "true"
        );

        launcher.setAttribute(
            "aria-expanded",
            "false"
        );

        launcher.focus();
    }


    // =========================================================
    // Messages
    // =========================================================

    function addMessage(
        text,
        sender = "assistant",
        isError = false
    ) {
        const row =
            document.createElement("div");

        row.className =
            `message-row ${sender}`;

        const bubble =
            document.createElement("div");

        bubble.className =
            "message-bubble";

        if (isError) {
            bubble.classList.add("error");
        }

        /*
            Important:
            textContent is intentional.

            Do NOT use innerHTML for chatbot responses.
            That prevents server/model output from
            injecting arbitrary HTML or JavaScript.
        */

        bubble.textContent = text;

        row.appendChild(bubble);

        messages.appendChild(row);

        scrollMessagesToBottom();
    }


    function showWelcomeMessage() {
        addMessage(
            "Hello! I’m the Sawai Associates AI Assistant. " +
            "I can help with Real Estate, Insurance, " +
            "IT Services, or general questions about " +
            "available services."
        );
    }


    function scrollMessagesToBottom() {
        messages.scrollTop =
            messages.scrollHeight;
    }


    // =========================================================
    // Menu buttons
    // =========================================================

    function clearOptions() {
        options.replaceChildren();
    }


    function renderOptions(items) {
        clearOptions();

        if (!Array.isArray(items)) {
            return;
        }

        items.forEach((item) => {

            let label = "";
            let action = null;
            let target = null;
            let value = null;

            if (typeof item === "string") {

                label = item.trim();
                value = label;

            } else if (
                item &&
                typeof item === "object"
            ) {

                label = String(
                    item.label
                    || item.title
                    || item.value
                    || ""
                ).trim();

                action =
                    typeof item.action === "string"
                        ? item.action
                        : null;

                target =
                    typeof item.target === "string"
                        ? item.target
                        : null;

                value =
                    typeof item.value === "string"
                        ? item.value
                        : label;
            }

            if (!label) {
                return;
            }

            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";

            button.className =
                "chat-option";

            button.textContent =
                label;

            button.addEventListener(
                "click",
                () => {

                    if (action) {

                        sendAction(
                            action,
                            target,
                            label
                        );

                    } else {

                        sendMessage(
                            value
                        );
                    }
                }
            );

            options.appendChild(
                button
            );
        });
    }


    // =========================================================
    // Progress / summary / deterministic actions
    // =========================================================

    function renderProgress(value) {
        if (
            typeof value !== "string" ||
            !value.trim()
        ) {
            progress.textContent = "";

            progress.classList.add(
                "hidden"
            );

            return;
        }

        progress.textContent =
            value;

        progress.classList.remove(
            "hidden"
        );
    }


    function renderSummary(items) {
        summary.replaceChildren();

        if (
            !Array.isArray(items) ||
            items.length === 0
        ) {
            summary.classList.add(
                "hidden"
            );

            return;
        }

        const title =
            document.createElement("div");

        title.className =
            "chat-summary-title";

        title.textContent =
            "Review your details";

        summary.appendChild(title);

        items.forEach((item) => {
            if (
                !item ||
                typeof item.label !== "string" ||
                typeof item.value !== "string"
            ) {
                return;
            }

            const row =
                document.createElement("div");

            row.className =
                "chat-summary-row";

            const label =
                document.createElement("span");

            label.className =
                "chat-summary-label";

            label.textContent =
                item.label;

            const value =
                document.createElement("span");

            value.className =
                "chat-summary-value";

            value.textContent =
                item.value;

            row.appendChild(label);

            row.appendChild(value);

            summary.appendChild(row);
        });

        summary.classList.remove(
            "hidden"
        );
    }


    function isSafeExternalUrl(
        rawUrl
    ) {
        try {
            const url =
                new URL(rawUrl);

            return (
                url.protocol === "https:"
            );
        } catch {
            return false;
        }
    }


    function renderActions(items) {
        actions.replaceChildren();

        if (!Array.isArray(items)) {
            return;
        }

        items.forEach((item) => {
            if (
                !item ||
                typeof item.label !== "string" ||
                typeof item.action !== "string"
            ) {
                return;
            }

            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";

            button.className =
                "chat-action";

            button.textContent =
                item.label;

            button.addEventListener(
                "click",
                () => {

                    if (
                        String(item)
                            .trim()
                            .toLowerCase()
                        === "talk to an expert"
                    ) {
                        trackAnalytics(
                            "expert_request"
                        );
                    }

                    sendMessage(item);
                }
            );

                        actions.appendChild(
                            button
                        );
                    });
                }


    // =========================================================
    // Loading state
    // =========================================================

    function setLoading(loading) {
        requestInProgress = loading;

        input.disabled = loading;

        sendButton.disabled = loading;

        if (loading) {
            typingIndicator.classList.remove(
                "hidden"
            );
        } else {
            typingIndicator.classList.add(
                "hidden"
            );
        }

        scrollMessagesToBottom();
    }


    // =========================================================
    // Shared API response handler
    // =========================================================

    function handleApiResponse(
        data
    ) {
        if (
            data &&
            typeof data.session_id === "string"
        ) {
            sessionId =
                data.session_id;

            localStorage.setItem(
                SESSION_STORAGE_KEY,
                sessionId
            );
        }

        const reply =
            data &&
            typeof data.reply === "string"
                ? data.reply
                : (
                    "I received the request, " +
                    "but couldn't display a response."
                );

        addMessage(
            reply,
            "assistant"
        );

        renderOptions(
            Array.isArray(
                data?.menu_options
            )
                ? data.menu_options
                : []
        );

        renderSummary(
            Array.isArray(
                data?.summary
            )
                ? data.summary
                : []
        );

        renderActions(
            Array.isArray(
                data?.actions
            )
                ? data.actions
                : []
        );

        renderProgress(
            data?.progress
        );
    }


    // =========================================================
    // API - natural language messages
    // =========================================================

    async function sendMessage(message) {

        /*
            Safety guard:
            Never convert action objects into
            "[object Object]".
        */
        if (
            message &&
            typeof message === "object"
        ) {

            if (
                typeof message.action ===
                "string"
            ) {

                return sendAction(
                    message.action,
                    message.target || null,
                    message.label
                    || message.title
                    || message.value
                    || message.action
                );
            }

            message =
                message.value
                || message.label
                || message.title
                || "";
        }


        const cleanMessage =
            String(
                message ?? ""
            ).trim();

        if (!cleanMessage) {
            return;
        }

        if (requestInProgress) {
            return;
        }

        if (cleanMessage.length > 2000) {
            addMessage(
                "Please keep your message under 2,000 characters.",
                "assistant",
                true
            );

            return;
        }

        clearOptions();

        addMessage(
            cleanMessage,
            "user"
        );

        input.value = "";

        resizeTextarea();

        setLoading(true);

        const payload = {
            message: cleanMessage
        };

        if (sessionId) {
            payload.session_id =
                sessionId;
        }

        try {
            const response =
                await fetch(
                    API_URL,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );

            let data = null;

            try {
                data =
                    await response.json();
            } catch {
                data = null;
            }

            if (!response.ok) {
                let errorMessage =
                    "I couldn't process that message. " +
                    "Please try again.";

                if (
                    response.status === 429
                ) {
                    errorMessage =
                        "There have been several requests in a short time. " +
                        "Please wait a moment and try again.";
                }

                if (
                    response.status === 422
                ) {
                    errorMessage =
                        "Please check your message and try again.";
                }

                throw new Error(
                    errorMessage
                );
            }

            handleApiResponse(
                data
            );

        } catch (error) {
            console.error(
                "Sawai chatbot request failed:",
                error
            );

            addMessage(
                error instanceof Error
                    ? error.message
                    : (
                        "The chat service is temporarily unavailable. " +
                        "Please try again."
                    ),
                "assistant",
                true
            );

        } finally {
            setLoading(false);

            input.focus();
        }
    }


    // =========================================================
    // API - deterministic UI actions
    // =========================================================

    async function sendAction(
        action,
        target = null,
        label = null
    ) {
        if (
            !action ||
            requestInProgress
        ) {
            return;
        }

        if (
            action === "request_call"
        ) {
            trackAnalytics(
                "call_request"
            );
        }


        if (
            action === "whatsapp"
        ) {
            trackAnalytics(
                "whatsapp_request"
            );
        }

        clearOptions();

        renderActions([]);

        renderSummary([]);

        if (label) {
            addMessage(
                label,
                "user"
            );
        }

        setLoading(true);

        const payload = {
            action
        };

        if (sessionId) {
            payload.session_id =
                sessionId;
        }

        if (target) {
            payload.target =
                target;
        }

        try {
            const response =
                await fetch(
                    API_URL,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );

            let data = null;

            try {
                data =
                    await response.json();
            } catch {
                data = null;
            }

            if (!response.ok) {
                if (
                    response.status === 429
                ) {
                    throw new Error(
                        "There have been several requests " +
                        "in a short time. Please wait a moment."
                    );
                }

                throw new Error(
                    "I couldn't complete that action. " +
                    "Please try again."
                );
            }

            handleApiResponse(
                data
            );

        } catch (error) {
            console.error(
                "Sawai chatbot action failed:",
                error
            );

            addMessage(
                error instanceof Error
                    ? error.message
                    : (
                        "The chat service is temporarily unavailable."
                    ),
                "assistant",
                true
            );

        } finally {
            setLoading(false);

            input.focus();
        }
    }

    async function trackAnalytics(
        eventType
    ) {
        const payload = {
            event_type: eventType
        };


        if (sessionId) {
            payload.session_id =
                sessionId;
        }


        try {
            await fetch(
                ANALYTICS_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

        } catch (
            error
        ) {
            /*
                Analytics must never break the
                customer chatbot.
            */

            console.debug(
                "Analytics event skipped:",
                error
            );
        }
    }


    // =========================================================
    // Reset conversation
    // =========================================================

    function resetConversation() {
        if (requestInProgress) {
            return;
        }

        sessionId = null;

        localStorage.removeItem(
            SESSION_STORAGE_KEY
        );

        messages.replaceChildren();

        clearOptions();

        renderSummary([]);

        renderActions([]);

        renderProgress(null);

        addMessage(
            "A new conversation has started. " +
            "How can I help you?"
        );

        input.value = "";

        resizeTextarea();

        input.focus();
    }


    // =========================================================
    // Textarea auto-resize
    // =========================================================

    function resizeTextarea() {
        input.style.height =
            "auto";

        input.style.height =
            Math.min(
                input.scrollHeight,
                110
            ) + "px";
    }


    // =========================================================
    // Event listeners
    // =========================================================

    launcher.addEventListener(
        "click",
        openChat
    );

    closeButton.addEventListener(
        "click",
        closeChat
    );

    resetButton.addEventListener(
        "click",
        resetConversation
    );

    form.addEventListener(
        "submit",
        (event) => {
            event.preventDefault();

            sendMessage(
                input.value
            );
        }
    );

    input.addEventListener(
        "input",
        resizeTextarea
    );

    /*
        Enter sends.
        Shift + Enter creates a new line.
    */

    input.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {
                event.preventDefault();

                sendMessage(
                    input.value
                );
            }
        }
    );

    /*
        ESC closes the widget.
    */

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape" &&
                chatWindow.classList.contains(
                    "open"
                )
            ) {
                closeChat();
            }
        }
    );

})();