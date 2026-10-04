import {
    useState,
    useEffect,
    useRef
} from "react"

import "./Chat.css"

import Markdown from "react-markdown"
import { API_BASE_URL } from "../api/request"


function Chat({
    chatList,
    setChatList,
    sessionId,
    setSessionId,
    loadSessions
}) {
    const [message, setMessage] = useState("")
    const [loading, setLoading] = useState(false)
const [agentMode, setAgentMode] = useState(false)

    const controllerRef = useRef(null)
    const bottomRef = useRef(null)


    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth"
        })
    }, [chatList])


    const stopGenerate = () => {
        if (controllerRef.current) {
            controllerRef.current.abort()
            controllerRef.current = null
        }

        setLoading(false)
    }


    const appendAiContent = (content) => {
        setChatList((list) => {
            if (list.length === 0) {
                return list
            }

            const newList = [...list]
            const lastIndex = newList.length - 1

            newList[lastIndex] = {
                ...newList[lastIndex],
                content:
                    (newList[lastIndex].content || "") +
                    (content || "")
            }

            return newList
        })
    }


    const appendAiStep = (step) => {
        setChatList((list) => {
            if (list.length === 0) {
                return list
            }

            const newList = [...list]
            const lastIndex = newList.length - 1

            newList[lastIndex] = {
                ...newList[lastIndex],
                steps: [
                    ...(newList[lastIndex].steps || []),
                    step
                ]
            }

            return newList
        })
    }


    const normalizeSources = (sources = []) => {
        const uniqueSources = []
        const sourceKeys = new Set()

        for (const source of sources) {
            if (!source || !source.filename) {
                continue
            }

            const key = source.filename

            if (sourceKeys.has(key)) {
                continue
            }

            sourceKeys.add(key)
            uniqueSources.push(source)
        }

        return uniqueSources
    }


    const setAiSources = (sources) => {
        setChatList((list) => {
            if (list.length === 0) {
                return list
            }

            const newList = [...list]
            const lastIndex = newList.length - 1

            newList[lastIndex] = {
                ...newList[lastIndex],
                sources: normalizeSources(sources)
            }

            return newList
        })
    }


    const handleSSE = (block) => {
        if (!block.trim()) {
            return
        }

        const lines = block.split("\n")

        let event = ""
        const dataLines = []

        for (const line of lines) {
            if (line.startsWith("event:")) {
                event = line
                    .slice(6)
                    .trim()
            }

            if (line.startsWith("data:")) {
                dataLines.push(
                    line
                        .slice(5)
                        .trim()
                )
            }
        }

        const data = dataLines.join("\n")

        if (!data) {
            return
        }

        try {
            if (event === "token") {
                const json = JSON.parse(data)

                appendAiContent(
                    json.content || ""
                )
            }


            if (event === "session") {
                const json = JSON.parse(data)

                setSessionId(
                    json.session_id
                )
            }


            if (event === "step") {
                const step = JSON.parse(data)

                appendAiStep(step)
            }

            if (event === "retry") {
                const retryStep = JSON.parse(data)

                appendAiStep(retryStep)
            }


            if (event === "sources") {
                const sources = JSON.parse(data)

                setAiSources(sources)
            }


            if (event === "error") {
                const json = JSON.parse(data)

                appendAiContent(
                    json.message ||
                    "AI生成失败"
                )
            }


            if (event === "done") {
                console.log("AI生成完成")
            }
        } catch (error) {
            console.error(
                "SSE解析失败",
                error,
                data
            )
        }
    }


    const consumeSSE = async (response) => {
        if (!response.body) {
            throw new Error(
                "浏览器不支持流式响应"
            )
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        let buffer = ""

        while (true) {
            const {
                done,
                value
            } = await reader.read()

            if (done) {
                break
            }

            buffer += decoder.decode(
                value,
                {
                    stream: true
                }
            )

            const blocks = buffer.split(
                "\n\n"
            )

            buffer = blocks.pop() || ""

            blocks.forEach((block) => {
                handleSSE(block)
            })
        }

        buffer += decoder.decode()

        if (buffer) {
            handleSSE(buffer)
        }
    }


    const sendMessage = async () => {
        if (!message.trim() || loading) {
            return
        }

        const text = message.trim()

        setMessage("")

        // 添加用户消息
        setChatList((list) => [
            ...list,
            {
                role: "user",
                content: text,
                create_time: new Date()
            }
        ])


        /*
         * Agent流式模式
         */
        if (agentMode) {
            // 先创建一个空的AI消息
            // 后续token会追加到这条消息中
            setChatList((list) => [
                ...list,
                {
                    role: "assistant",
                    content: "",
                    sources: [],
                    steps: [],
                    create_time: new Date()
                }
            ])

            setLoading(true)

            const controller = new AbortController()
            controllerRef.current = controller

            try {
                const response = await fetch(
                    `${API_BASE_URL}/agent/chat/stream`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                            "Authorization":
                                "Bearer " +
                                localStorage.getItem(
                                    "token"
                                )
                        },

                        body: JSON.stringify({
                            message: text,
                            session_id:
                                sessionId || null
                        }),

                        signal: controller.signal
                    }
                )

                if (!response.ok) {
                    throw new Error(
                        `Agent请求失败：${response.status}`
                    )
                }

                await consumeSSE(response)

                if (!sessionId) {
                    loadSessions()
                }
            } catch (error) {
                if (error.name === "AbortError") {
                    console.log(
                        "用户停止了Agent生成"
                    )
                } else {
                    console.error(
                        "Agent流式请求失败",
                        error
                    )

                    appendAiContent(
                        "Agent执行失败，请稍后重试"
                    )
                }
            } finally {
                setLoading(false)
                controllerRef.current = null
            }

            return
        }


        /*
         * 普通聊天流式模式
         */
        setChatList((list) => [
            ...list,
            {
                role: "assistant",
                content: "",
                sources: [],
                steps: [],
                create_time: new Date()
            }
        ])

        setLoading(true)

        const controller = new AbortController()
        controllerRef.current = controller

        try {
            const response = await fetch(
                `${API_BASE_URL}/chat/stream`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                        "Authorization":
                            "Bearer " +
                            localStorage.getItem(
                                "token"
                            )
                    },

                    body: JSON.stringify({
                        message: text,
                        session_id:
                            sessionId || null
                    }),

                    signal: controller.signal
                }
            )

            if (!response.ok) {
                throw new Error(
                    `请求失败：${response.status}`
                )
            }

            await consumeSSE(response)

            if (!sessionId) {
                loadSessions()
            }
        } catch (error) {
            if (error.name === "AbortError") {
                console.log(
                    "用户停止了生成"
                )
            } else {
                console.error(
                    "普通聊天请求失败",
                    error
                )

                appendAiContent(
                    "请求失败，请稍后重试"
                )
            }
        } finally {
            setLoading(false)
            controllerRef.current = null
        }
    }


    return (
        <div className="chat-container">
            <h1>
                AI Agent Chat
            </h1>


            <div className="chat-box">
                {
                    chatList.map((item, index) => (
                        <div
                            key={index}
                            className={
                                item.role === "user"
                                    ? "message user"
                                    : "message ai"
                            }
                        >
                            <div className="avatar">
                                {
                                    item.role === "user"
                                        ? "👤"
                                        : "🤖"
                                }
                            </div>


                            <div className="content">
                                <Markdown>
                                    {item.content || ""}
                                </Markdown>


                                {
                                    item.role ===
                                    "assistant" &&
                                    item.steps?.length > 0 &&
                                    (
                                        <div className="sources">
                                            <div className="sources-title">
                                                ⚙️ 执行过程
                                            </div>

                                            {
                                                item.steps.map(
                                                    (
                                                        step,
                                                        stepIndex
                                                    ) => (
                                                        <div
                                                            key={
                                                                stepIndex
                                                            }
                                                            className={
                                                                 step.status === "retrying"
                                                                      ? "source-item retrying"
                                                                      : "source-item"
                                                            }
                                                        >
                                                            {
                                                                step.status ===
                                                                "running"
                                                                    ? "⏳"
                                                                    : step.status ===
                                                                      "retrying"
                                                                      ? "🔄"
                                                                      :step.status ===
                                                                      "success"
                                                                        ? "✅"
                                                                        : "❌"
                                                            }

                                                            {" "}

                                                            {
                                                                step.message
                                                            }
                                                        </div>
                                                    )
                                                )
                                            }
                                        </div>
                                    )
                                }


                                {
                                    item.role ===
                                    "assistant" &&
                                    item.sources?.length > 0 &&
                                    (
                                        <div className="sources">
                                            <div className="sources-title">
                                                📎 参考来源
                                            </div>

                                            {
                                                item.sources.map(
                                                    (
                                                        source,
                                                        sourceIndex
                                                    ) => (
                                                        <div
                                                            key={
                                                                sourceIndex
                                                            }
                                                            className="source-item"
                                                        >
                                                            📄{" "}
                                                            {
                                                                source.filename
                                                            }
                                                        </div>
                                                    )
                                                )
                                            }
                                        </div>
                                    )
                                }
                            </div>


                            <div className="time">
                                {
                                    item.create_time
                                        ? new Date(
                                            item.create_time
                                        ).toLocaleTimeString(
                                            [],
                                            {
                                                hour: "2-digit",
                                                minute: "2-digit"
                                            }
                                        )
                                        : ""
                                }
                            </div>
                        </div>
                    ))
                }


                {
                    loading && (
                        <div className="ai-loading">
                            🤖 AI正在生成...
                        </div>
                    )
                }

                <div ref={bottomRef}></div>
            </div>


            <div className="input-area">
                <label>
                    <input
                        type="checkbox"
                        checked={agentMode}
                        onChange={(event) => {
                            setAgentMode(
                                event.target.checked
                            )
                        }}
                    />

                    Agent模式
                </label>


                <input
                    value={message}
                    onChange={(event) => {
                        setMessage(
                            event.target.value
                        )
                    }}
                    placeholder="请输入问题"
                    onKeyDown={(event) => {
                        if (
                            event.key === "Enter" &&
                            !event.shiftKey
                        ) {
                            event.preventDefault()
                            sendMessage()
                        }
                    }}
                />


                {
                    loading ? (
                        <button
                            onClick={stopGenerate}
                        >
                            停止生成
                        </button>
                    ) : (
                        <button
                            onClick={sendMessage}
                        >
                            发送
                        </button>
                    )
                }
            </div>
        </div>
    )
}


export default Chat
