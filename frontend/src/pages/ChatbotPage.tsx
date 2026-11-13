// =============================================================================
// PROJECT NEXUS AI - Chatbot Page
// =============================================================================

import { useState, useEffect } from 'react'
import { Layout } from '@/components/Layout'
import { chatbotAPI } from '@/services/api'
import { Loader2, Send, RotateCcw } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export function ChatbotPage() {
  const [conversations, setConversations] = useState<any[]>([])
  const [activeConversation, setActiveConversation] = useState<any>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const response = await chatbotAPI.listConversations()
      setConversations(response.data)
      if (response.data.length > 0) {
        selectConversation(response.data[0].id)
      }
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load conversations')
      }
    }
  }

  const selectConversation = async (id: string) => {
    const conv = conversations.find((c) => c.id === id) || null
    setActiveConversation(conv)
    if (conv) {
      try {
        const response = await chatbotAPI.getMessages(id)
        setMessages(response.data)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load messages')
      }
    }
  }

  const createConversation = async () => {
    try {
      const response = await chatbotAPI.createConversation({ title: 'New Investigation' })
      setConversations([response.data, ...conversations])
      selectConversation(response.data.id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create conversation')
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !activeConversation) return

    const userMessage: Message = {
      id: 'temp',
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    }
    setMessages([...messages, userMessage])
    setInput('')
    setSending(true)

    try {
      const response = await chatbotAPI.sendMessage(activeConversation.id, input)
      setMessages([...messages, userMessage, response.data.assistant_message])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <Layout>
      <div className="flex h-[calc(100vh-4rem)] flex-col">
        <div className="flex h-full">
          {/* Sidebar - Conversations */}
          <div className="w-80 bg-slate-900 border-r border-slate-700 flex flex-col">
            <div className="p-4 border-b border-slate-700">
              <h3 className="font-semibold text-white">Conversations</h3>
              <button
                onClick={createConversation}
                className="w-full btn-secondary mt-3 text-xs py-2"
              >
                <RotateCcw size={14} className="mr-2" />
                New Conversation
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {conversations.length === 0 && (
                <p className="text-xs text-slate-500 text-center py-4">No conversations</p>
              )}
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => selectConversation(c.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    activeConversation?.id === c.id ? 'bg-nexus-accent/20 text-nexus-accent' : 'text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <p className="text-sm truncate">{c.title || 'Untitled'}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Chat Area */}
          <div className="flex-1 flex flex-col bg-slate-800/50">
            {activeConversation ? (
              <>
                <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white">{activeConversation.title}</h3>
                    <p className="text-xs text-slate-500">NEXUS AI Forensic Assistant</p>
                  </div>
                </div>
                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm mx-4 mb-4">
                    <span>{error}</span>
                  </div>
                )}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.length === 0 && (
                    <div className="text-center py-10 text-slate-500">
                      <p>Start a conversation with the NEXUS AI forensic assistant.</p>
                    </div>
                  )}
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[80%] p-3 rounded-lg ${
                        m.role === 'user'
                          ? 'bg-nexus-accent text-white'
                          : 'bg-slate-700 text-slate-200'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                        <p className="text-xs text-opacity-60 mt-1">
                          {new Date(m.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))}
                  {sending && (
                    <div className="flex justify-start">
                      <div className="bg-slate-700 p-3 rounded-lg animate-pulse">
                        <div className="h-4 bg-slate-600 rounded w-24 mb-1" />
                        <div className="h-4 bg-slate-600 rounded w-16" />
                      </div>
                    </div>
                  )}
                </div>
                <form onSubmit={sendMessage} className="p-4 border-t border-slate-700 bg-slate-900">
                  <div className="flex gap-2">
                    <input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask about your forensic investigation..."
                      className="flex-1 input"
                      disabled={sending}
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || sending}
                      className="btn-primary"
                    >
                      {sending ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Send size={16} />
                      )}
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
                <p>Select a conversation or create a new one.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
