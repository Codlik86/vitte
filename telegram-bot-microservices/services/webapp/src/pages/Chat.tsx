import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { sendChatMessage, getGreeting } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { tg } from "../lib/telegram";
import { getAvatarPaths } from "../lib/avatars";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

type LocationState = {
  personaId?: number;
  personaName?: string;
  personaKey?: string;
  storyId?: string;
  atmosphere?: string;
  greeting?: string;
  dialogId?: number;
  isReturn?: boolean;
};

export function Chat() {
  const { dialogId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as LocationState) ?? {};
  const { data: accessStatus } = useAccessStatus();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingGreeting, setLoadingGreeting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const personaName = state.personaName ?? "Персонаж";
  const personaKey = state.personaKey ?? "";
  const avatarUrl = personaKey ? getAvatarPaths(personaKey, false).chat : undefined;

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load greeting on mount
  useEffect(() => {
    const loadInitial = async () => {
      // If greeting was passed from previous page
      if (state.greeting) {
        setMessages([
          {
            id: `greeting-${Date.now()}`,
            role: "assistant",
            content: state.greeting,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      // Otherwise fetch greeting
      if (state.personaId) {
        setLoadingGreeting(true);
        try {
          const result = await getGreeting({
            persona_id: state.personaId,
            story_id: state.storyId,
            atmosphere: state.atmosphere,
            is_return: state.isReturn ?? false,
          });
          if (result.success && result.response) {
            setMessages([
              {
                id: `greeting-${Date.now()}`,
                role: "assistant",
                content: result.response,
                timestamp: new Date(),
              },
            ]);
          }
        } catch (e: any) {
          setError(e.message ?? "Ошибка загрузки");
        } finally {
          setLoadingGreeting(false);
        }
      }
    };
    loadInitial();
  }, []);

  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || sending) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setSending(true);
    setError(null);

    try {
      const result = await sendChatMessage({
        message: text,
        persona_id: state.personaId,
        story_id: state.storyId,
        atmosphere: state.atmosphere,
      });

      if (result.success && result.response) {
        const assistantMsg: Message = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.response,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else if (result.error) {
        setError(result.error);
      }
    } catch (e: any) {
      setError(e.message ?? "Ошибка отправки");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-bg-dark/90 backdrop-blur-sm border-b border-white/5">
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            onClick={() => navigate(-1)}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
          </button>
          {avatarUrl && (
            <img
              src={avatarUrl}
              alt={personaName}
              className="h-10 w-10 rounded-full object-cover"
            />
          )}
          <div className="flex-1">
            <h1 className="text-base font-semibold text-white">{personaName}</h1>
            <p className="text-xs text-white/50">онлайн</p>
          </div>
          <button
            onClick={() => navigate("/dialogs")}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {loadingGreeting && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-white/10 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="loading-dots">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "rounded-br-md bg-gradient-to-r from-purple-600 to-pink-500 text-white"
                  : "rounded-bl-md bg-white/10 text-white"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-white/10 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="loading-dots">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="sticky bottom-0 border-t border-white/5 bg-bg-dark/90 backdrop-blur-sm p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Напиши сообщение..."
            rows={1}
            className="flex-1 resize-none rounded-2xl bg-white/10 px-4 py-3 text-sm text-white placeholder-white/40 outline-none focus:ring-1 focus:ring-white/20"
            style={{ minHeight: "44px", maxHeight: "120px" }}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || sending}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-r from-purple-600 to-pink-500 text-white disabled:opacity-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
