"use client";

import { useState, useRef, useEffect } from "react";
import { 
  Bot, Send, User, Sparkles, MapPin, Star, Globe, 
  Phone, Download, Loader2, Trash2
} from "lucide-react";
import { aiApi, exportsApi } from "@/lib/api";
import type { ExportFormat } from "@/types";
import { useToast } from "@/components/Providers";

interface ChatMessage {
  sender: "user" | "bot";
  text: string;
  timestamp: Date;
}

interface ScrapedPlace {
  name: string;
  category?: string;
  rating?: number;
  total_reviews?: number;
  address?: string;
  phone?: string;
  website?: string;
  maps_url?: string;
}

export default function AIAssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: "bot",
      text: "Hello! I am your AI Reviews Assistant. Tell me the name of any location or business (e.g. **Sofa Gold Mall**), and I will search Google Maps, scrape its reviews, and answer any questions you have about them.",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [place, setPlace] = useState<ScrapedPlace | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  
  const { addToast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Handle sending a message
  const handleSend = async (messageText: string = input) => {
    const trimmed = messageText.trim();
    if (!trimmed) return;

    // Add user message
    const userMsg: ChatMessage = {
      sender: "user",
      text: trimmed,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    if (messageText === input) setInput("");
    setLoading(true);

    try {
      const res = await aiApi.chat({
        message: trimmed,
        session_id: sessionId || undefined,
        max_reviews: 100
      });

      if (res.success && res.data) {
        const data = res.data;
        if (data.session_id) setSessionId(data.session_id);
        
        // Add bot message
        setMessages(prev => [...prev, {
          sender: "bot",
          text: data.reply,
          timestamp: new Date()
        }]);

        // If place info was returned, load it
        if (data.scraped_place) {
          setPlace(data.scraped_place as ScrapedPlace);
          addToast(`Scraped place loaded: ${data.scraped_place.name}`, "success");
        }

        // If a scraper job was run, set jobId
        if (data.job_id) {
          setJobId(data.job_id);
        }
      } else {
        addToast(res.message || "Failed to get AI response", "error");
        setMessages(prev => [...prev, {
          sender: "bot",
          text: "I encountered an error connecting to the API. Please ensure your backend is running and has a valid GEMINI_API_KEY configured.",
          timestamp: new Date()
        }]);
      }
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      const errorMsg = error.response?.data?.detail || "Backend server unreachable.";
      addToast(errorMsg, "error");
      setMessages(prev => [...prev, {
        sender: "bot",
        text: `Error: ${errorMsg}`,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Export current job reviews
  const handleExport = async (format: "json" | "csv" | "excel") => {
    if (!jobId) {
      addToast("No scraping job was executed in this chat yet.", "error");
      return;
    }
    try {
      addToast(`Generating ${format.toUpperCase()} export...`, "info");
      const res = await exportsApi.create(jobId, format as ExportFormat);
      if (res.success && res.data) {
        addToast("Export generated successfully!", "success");
        // Open download url
        window.open(exportsApi.downloadUrl(res.data.file), "_blank");
      } else {
        addToast(res.message || "Export failed", "error");
      }
    } catch {
      addToast("Error generating export", "error");
    }
  };

  // Format message text with markdown-like bold text **text**
  const renderMessageText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  // Quick action suggestions
  const suggestions = [
    { text: "extract reviews of Sofa Gold Mall", label: "Sofa Gold Mall reviews", action: true },
    { text: "What are the common pros and cons?", label: "Pros & Cons list" },
    { text: "What do people say about customer service?", label: "Customer service info" },
    { text: "Are there any complaints about prices or delivery?", label: "Pricing feedback" }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 40px)", overflow: "hidden" }}>
      {/* Header */}
      <div className="page-header" style={{ paddingBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ 
              width: 40, height: 40, borderRadius: 10, 
              background: "linear-gradient(135deg, var(--accent-blue), #3b82f6)", 
              display: "flex", alignItems: "center", justifyContent: "center" 
            }}>
              <Bot size={20} color="white" />
            </div>
            <div>
              <h1 className="page-title">AI Reviews Assistant</h1>
              <p className="page-subtitle">Scrape review data instantly and chat with Gemini to analyze feedback</p>
            </div>
          </div>
          {sessionId && (
            <button 
              className="btn btn-secondary" 
              onClick={() => {
                setSessionId("");
                setPlace(null);
                setJobId(null);
                setMessages([
                  {
                    sender: "bot",
                    text: "Session cleared! Tell me the name of any location or business (e.g. Sofa Gold Mall), and I'll search Google Maps and scrape its reviews.",
                    timestamp: new Date()
                  }
                ]);
                addToast("Chat session reset successfully.", "success");
              }}
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, padding: "8px 12px" }}
            >
              <Trash2 size={14} /> Clear Chat
            </button>
          )}
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="page-body" style={{ 
        flex: 1, 
        display: "grid", 
        gridTemplateColumns: "1fr 340px", 
        gap: 20, 
        overflow: "hidden", 
        paddingBottom: 10 
      }}>
        
        {/* Left Side: Chat Panel */}
        <div className="card" style={{ 
          display: "flex", 
          flexDirection: "column", 
          overflow: "hidden",
          padding: 0,
          background: "var(--bg-card)",
          border: "1px solid var(--border)"
        }}>
          
          {/* Messages Area */}
          <div style={{ 
            flex: 1, 
            overflowY: "auto", 
            padding: "24px 24px 12px", 
            display: "flex", 
            flexDirection: "column", 
            gap: 16 
          }}>
            {messages.map((msg, i) => (
              <div 
                key={i} 
                style={{ 
                  display: "flex", 
                  gap: 12, 
                  alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                  maxWidth: "80%",
                  flexDirection: msg.sender === "user" ? "row-reverse" : "row"
                }}
              >
                {/* Avatar */}
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: msg.sender === "user" 
                    ? "rgba(59,130,246,0.15)" 
                    : "rgba(16,185,129,0.12)",
                  color: msg.sender === "user" 
                    ? "var(--accent-blue)" 
                    : "var(--accent-emerald)",
                  border: msg.sender === "user"
                    ? "1px solid rgba(59,130,246,0.2)"
                    : "1px solid rgba(16,185,129,0.2)",
                  flexShrink: 0
                }}>
                  {msg.sender === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>

                {/* Message Bubble */}
                <div style={{
                  background: msg.sender === "user" 
                    ? "var(--gradient-brand)" 
                    : "var(--bg-card-hover)",
                  color: msg.sender === "user" 
                    ? "white" 
                    : "var(--text-secondary)",
                  padding: "12px 16px",
                  borderRadius: msg.sender === "user" 
                    ? "12px 0 12px 12px" 
                    : "0 12px 12px 12px",
                  fontSize: 14,
                  lineHeight: 1.5,
                  boxShadow: msg.sender === "user"
                    ? "0 4px 12px rgba(59,130,246,0.2)"
                    : "none",
                  border: msg.sender === "user" 
                    ? "none" 
                    : "1px solid var(--border)",
                  whiteSpace: "pre-wrap"
                }}>
                  {renderMessageText(msg.text)}
                  <div style={{ 
                    fontSize: 10, 
                    opacity: 0.6, 
                    textAlign: msg.sender === "user" ? "right" : "left", 
                    marginTop: 6 
                  }}>
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}
            
            {loading && (
              <div style={{ display: "flex", gap: 12, alignSelf: "flex-start" }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: "rgba(16,185,129,0.12)", color: "var(--accent-emerald)",
                  border: "1px solid rgba(16,185,129,0.2)"
                }}>
                  <Bot size={16} />
                </div>
                <div style={{
                  background: "var(--bg-card-hover)",
                  color: "var(--text-muted)",
                  padding: "12px 16px",
                  borderRadius: "0 12px 12px 12px",
                  fontSize: 14,
                  border: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  gap: 12
                }}>
                  <Loader2 size={16} className="animate-spin" />
                  <span>AI is thinking & scraping reviews... This might take 10-30 seconds.</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick suggestions above input */}
          <div style={{ 
            padding: "8px 24px", 
            borderTop: "1px solid var(--border)",
            display: "flex",
            gap: 8,
            overflowX: "auto",
            background: "rgba(0,0,0,0.05)",
            flexWrap: "nowrap"
          }}>
            {suggestions.map((sug, i) => (
              <button
                key={i}
                className="btn btn-secondary"
                onClick={() => handleSend(sug.text)}
                disabled={loading}
                style={{ 
                  fontSize: 11, 
                  padding: "6px 12px", 
                  borderRadius: 20, 
                  whiteSpace: "nowrap",
                  display: "flex",
                  alignItems: "center",
                  gap: 4
                }}
              >
                {sug.action && <Sparkles size={11} color="var(--accent-blue)" />}
                {sug.label}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div style={{ padding: 20, borderTop: "1px solid var(--border)" }}>
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }} 
              style={{ display: "flex", gap: 12 }}
            >
              <input
                type="text"
                className="input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question or enter a business name to scrape..."
                disabled={loading}
                style={{ flex: 1, padding: "12px 16px" }}
              />
              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={loading || !input.trim()}
                style={{ width: 48, height: 48, borderRadius: 10, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
              >
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Place Details Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20, overflowY: "auto" }}>
          
          {/* place card */}
          {place ? (
            <div className="card" style={{ padding: 20, border: "1px solid var(--border)", background: "var(--bg-card)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent-blue)", marginBottom: 12 }}>
                <MapPin size={16} />
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>Target Place Loaded</span>
              </div>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginBottom: 6, lineHeight: 1.2 }}>
                {place.name}
              </h2>
              {place.category && (
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
                  {place.category}
                </div>
              )}

              {place.rating !== undefined && (
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.15)", borderRadius: 8, padding: "8px 12px" }}>
                  <Star size={18} fill="#f59e0b" color="#f59e0b" />
                  <span style={{ fontWeight: 800, fontSize: 16, color: "var(--text-primary)" }}>{place.rating}</span>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>({place.total_reviews?.toLocaleString()} Google reviews)</span>
                </div>
              )}

              {/* metadata */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--border)", paddingTop: 16, marginBottom: 20 }}>
                {place.address && (
                  <div style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 12 }}>
                    <MapPin size={14} style={{ color: "var(--text-muted)", flexShrink: 0, marginTop: 2 }} />
                    <span style={{ color: "var(--text-secondary)" }}>{place.address}</span>
                  </div>
                )}
                {place.phone && (
                  <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }}>
                    <Phone size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                    <span style={{ color: "var(--text-secondary)" }}>{place.phone}</span>
                  </div>
                )}
                {place.website && (
                  <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }}>
                    <Globe size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                    <a href={place.website} target="_blank" rel="noreferrer" className="link-hover" style={{ color: "var(--accent-blue)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      Visit Website
                    </a>
                  </div>
                )}
              </div>

              {/* Exports options */}
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 12, letterSpacing: "0.05em" }}>
                  Save/Download Reviews
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
                  <button className="btn btn-secondary" onClick={() => handleExport("json")} style={{ fontSize: 12, padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                    <Download size={12} /> JSON
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleExport("excel")} style={{ fontSize: 12, padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                    <Download size={12} /> Excel
                  </button>
                </div>
                <button className="btn btn-secondary" onClick={() => handleExport("csv")} style={{ width: "100%", fontSize: 12, padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                  <Download size={12} /> Export CSV File
                </button>
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: 24, textAlign: "center", border: "1px dashed var(--border)", background: "rgba(0,0,0,0.05)" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "rgba(59,130,246,0.1)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                <Sparkles size={20} color="var(--accent-blue)" />
              </div>
              <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-secondary)", marginBottom: 6 }}>No reviews loaded yet</div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.4 }}>
                Enter the name of a business (e.g. &quot;Sofa Gold Mall&quot;) in the chat to start scraping reviews.
              </p>
            </div>
          )}

          {/* Quick guide card */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>Quick Guide</div>
            <ul style={{ paddingLeft: 16, margin: 0, fontSize: 12, color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: 8 }}>
              <li>Type **Sofa Gold Mall** to trigger Google Maps search & reviews scraping.</li>
              <li>Wait while the scraper navigates Maps, finds the business, and extracts the reviews feed.</li>
              <li>Ask Gemini to summarize the feedback, evaluate client sentiment, or detect price complaints.</li>
            </ul>
          </div>
          
        </div>
      </div>
    </div>
  );
}
