import React, { useState, useRef, useEffect } from 'react';
import { 
  Terminal, 
  Cpu, 
  Send, 
  CheckCircle2, 
  XCircle, 
  Sparkles, 
  Bot, 
  User, 
  CornerDownLeft,
  CheckSquare,
  Square,
  Trash2,
  Plus,
  ShieldAlert,
  Activity,
  Layers,
  Wrench,
  Mic,
  MicOff,
  RotateCcw,
  FolderOpen,
  Code
} from 'lucide-react';

interface PendingAction {
  action_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  status: string;
}

interface Message {
  sender: 'user' | 'apex';
  text: string;
  action?: PendingAction;
}

interface Task {
  id: number;
  title: string;
  completed: boolean;
  created_at: string;
}

interface AuditLog {
  id: number;
  tool_name: string;
  arguments: string;
  status: string;
  timestamp: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'agent' | 'tasks' | 'logs'>('agent');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'apex',
      text: 'Apex Local Agent initialized. Connected to local runtime (qwen/qwen3-4b). How can I assist you with your workspace?'
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);

  // Mic state
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskInput, setNewTaskInput] = useState('');
  const [logs, setLogs] = useState<AuditLog[]>([]);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/history')
      .then(res => res.json())
      .then(data => {
        if (data.history && data.history.length > 0) {
          setMessages(data.history);
        }
      })
      .catch(() => console.log('Fresh session mode'));
    
    loadTasks();
    loadLogs();
  }, []);

  useEffect(() => {
    if (activeTab === 'agent') {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, activeTab]);

  // Offline Native Speech-to-Text Setup
  const toggleSpeech = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser shell.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(prev => (prev ? `${prev} ${transcript}` : transcript));
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const handleNewChat = async () => {
    await fetch('http://127.0.0.1:8000/api/clear', { method: 'POST' }).catch(() => {});
    setMessages([
      {
        sender: 'apex',
        text: 'New session started. Workspace ready for commands or code execution.'
      }
    ]);
    setActiveAction(null);
  };

  const triggerQuickTool = async (promptText: string) => {
    setInput(promptText);
    setTimeout(() => {
      const sendBtn = document.getElementById('apex-send-btn');
      sendBtn?.click();
    }, 50);
  };

  const loadTasks = () => {
    fetch('http://127.0.0.1:8000/api/tasks')
      .then(res => res.json())
      .then(data => setTasks(data.tasks || []))
      .catch(() => {});
  };

  const loadLogs = () => {
    fetch('http://127.0.0.1:8000/api/logs')
      .then(res => res.json())
      .then(data => setLogs(data.logs || []))
      .catch(() => {});
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskInput.trim()) return;

    await fetch('http://127.0.0.1:8000/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTaskInput.trim() })
    });
    setNewTaskInput('');
    loadTasks();
  };

  const handleToggleTask = async (id: number) => {
    await fetch(`http://127.0.0.1:8000/api/tasks/${id}/toggle`, { method: 'POST' });
    loadTasks();
  };

  const handleDeleteTask = async (id: number) => {
    await fetch(`http://127.0.0.1:8000/api/tasks/${id}`, { method: 'DELETE' });
    loadTasks();
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      });

      const data = await res.json();

      if (data.type === 'action_proposal' && data.pending_action) {
        setActiveAction(data.pending_action);
        setMessages(prev => [
          ...prev, 
          { 
            sender: 'apex', 
            text: data.reply || `Proposed action: ${data.pending_action.tool_name}`, 
            action: data.pending_action 
          }
        ]);
      } else {
        setMessages(prev => [...prev, { sender: 'apex', text: data.reply || 'Task processed.' }]);
      }
      loadLogs();
    } catch {
      setMessages(prev => [
        ...prev, 
        { 
          sender: 'apex', 
          text: 'Backend Offline: Ensure FastAPI is running on port 8000 and LM Studio is responding on 1234.' 
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleApproval = async (actionId: string, approved: boolean) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, approved })
      });
      const data = await res.json();

      if (data.self_healing && data.pending_action) {
        setActiveAction(data.pending_action);
        setMessages(prev => [
          ...prev,
          {
            sender: 'apex',
            text: `${data.result}\n\n⚠️ Self-Healing Engine: A code patch has been generated. Review and approve the patch below:`,
            action: data.pending_action
          }
        ]);
      } else {
        setActiveAction(null);
        setMessages(prev => [
          ...prev,
          {
            sender: 'apex',
            text: approved ? `Execution result: ${data.result}` : 'Action execution was cancelled.'
          }
        ]);
      }
      loadLogs();
    } catch {
      alert('Approval signal failed to reach local engine.');
    }
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-[#07080c] text-neutral-100 font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293d0d_1px,transparent_1px),linear-gradient(to_bottom,#1f293d0d_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none"></div>
      <div className="absolute top-[-10%] left-[-10%] w-[35vw] h-[35vw] rounded-full bg-emerald-500/5 blur-[140px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[35vw] h-[35vw] rounded-full bg-cyan-500/5 blur-[140px] pointer-events-none"></div>

      {/* Sidebar Navigation */}
      <aside className="relative z-10 w-72 shrink-0 border-r border-neutral-800/60 bg-[#0a0c12]/80 backdrop-blur-2xl flex flex-col justify-between p-4">
        <div className="space-y-5">
          
          {/* Logo Header */}
          <div className="flex items-center gap-3 px-2 py-1">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center font-bold text-base text-black shadow-lg shadow-emerald-500/20 border border-emerald-300/30">
              A
            </div>
            <div>
              <h1 className="font-semibold text-sm tracking-wide text-neutral-100 flex items-center gap-1.5">
                APEX AI <span className="text-[10px] text-neutral-500 font-mono">OS</span>
              </h1>
              <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1.5 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE LOCAL RUNTIME
              </span>
            </div>
          </div>

          {/* New Chat Primary Action Button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-neutral-900/90 hover:bg-neutral-800 border border-neutral-700/60 text-neutral-200 text-xs font-medium transition cursor-pointer shadow-sm group"
          >
            <RotateCcw size={13} className="text-emerald-400 group-hover:rotate-[-45deg] transition-transform" />
            New Session / Clear Chat
          </button>

          {/* Navigation Buttons */}
          <nav className="space-y-1.5 text-xs font-medium">
            <button
              onClick={() => setActiveTab('agent')}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition cursor-pointer ${
                activeTab === 'agent' 
                  ? 'bg-neutral-800/90 text-white shadow-inner border border-neutral-700/70' 
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60'
              }`}
            >
              <Terminal size={15} className={activeTab === 'agent' ? 'text-emerald-400' : 'text-neutral-500'} />
              Workspace & Agent
            </button>
            <button
              onClick={() => { setActiveTab('tasks'); loadTasks(); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition cursor-pointer ${
                activeTab === 'tasks' 
                  ? 'bg-neutral-800/90 text-white shadow-inner border border-neutral-700/70' 
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60'
              }`}
            >
              <CheckSquare size={15} className={activeTab === 'tasks' ? 'text-emerald-400' : 'text-neutral-500'} />
              Tasks & Goals
            </button>
            <button
              onClick={() => { setActiveTab('logs'); loadLogs(); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition cursor-pointer ${
                activeTab === 'logs' 
                  ? 'bg-neutral-800/90 text-white shadow-inner border border-neutral-700/70' 
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60'
              }`}
            >
              <Activity size={15} className={activeTab === 'logs' ? 'text-emerald-400' : 'text-neutral-500'} />
              System Audit Logs
            </button>
          </nav>

          {/* Quick OS Launcher Shortcuts */}
          <div className="pt-2 border-t border-neutral-800/60 space-y-2">
            <div className="text-[11px] text-neutral-500 uppercase tracking-wider font-semibold px-2">
              Quick Workspace Tools
            </div>
            <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
              <button
                onClick={() => triggerQuickTool('open explorer')}
                className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-neutral-950/60 border border-neutral-800/80 hover:border-neutral-700 text-neutral-300 transition text-[11px] cursor-pointer"
              >
                <FolderOpen size={12} className="text-amber-400" /> Explorer
              </button>
              <button
                onClick={() => triggerQuickTool('open vs code')}
                className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-neutral-950/60 border border-neutral-800/80 hover:border-neutral-700 text-neutral-300 transition text-[11px] cursor-pointer"
              >
                <Code size={12} className="text-cyan-400" /> VS Code
              </button>
            </div>
          </div>
        </div>

        {/* Runtime Spec Card */}
        <div className="p-3.5 bg-neutral-950/70 border border-neutral-800/80 rounded-2xl text-xs space-y-1.5 backdrop-blur-md">
          <div className="flex items-center justify-between text-neutral-300 font-medium">
            <div className="flex items-center gap-2 truncate">
              <Cpu size={14} className="text-emerald-400 shrink-0" />
              <span className="truncate">qwen/qwen3-4b</span>
            </div>
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </div>
          <div className="text-[11px] text-neutral-500 font-mono">
            Host: 127.0.0.1:1234 (Local)
          </div>
        </div>
      </aside>

      {/* Main App Container */}
      <main className="relative z-10 flex-1 flex flex-col min-w-0 h-full bg-[#0a0c12]/40 backdrop-blur-sm">
        
        {/* Top Header */}
        <header className="h-14 shrink-0 border-b border-neutral-800/60 px-6 flex items-center justify-between bg-neutral-900/20 backdrop-blur-md">
          <div className="flex items-center gap-2 text-xs font-mono text-neutral-400 truncate">
            <Layers size={14} className="text-neutral-500 shrink-0" />
            <span className="text-neutral-500">Workspace:</span>
            <span className="text-neutral-300 font-medium truncate">sandbox\</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-3 py-1 rounded-full flex items-center gap-1.5 font-medium shadow-sm">
              <Sparkles size={11} className="text-emerald-400" /> 100% Private Offline
            </span>
          </div>
        </header>

        {/* Tab 1: Workspace & Agent */}
        {activeTab === 'agent' && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Scrollable Chat Area */}
            <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
              <div className="max-w-4xl mx-auto space-y-5">
                {messages.map((m, idx) => {
                  const targetAction = m.action || (idx === messages.length - 1 ? activeAction : null);
                  const isHealing = Boolean(
                    targetAction?.tool_name === 'create_local_file' && 
                    typeof targetAction?.arguments?.content === 'string' &&
                    targetAction.arguments.content.includes('except')
                  );

                  return (
                    <div
                      key={idx}
                      className={`flex gap-3.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {m.sender === 'apex' && (
                        <div className="h-8 w-8 rounded-xl bg-[#12141c] border border-neutral-800 flex items-center justify-center shrink-0 mt-0.5 text-neutral-300 shadow-md">
                          <Bot size={16} className="text-emerald-400" />
                        </div>
                      )}

                      <div
                        className={`max-w-2xl px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                          m.sender === 'user'
                            ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-tr-sm shadow-lg shadow-emerald-950/40 border border-emerald-400/20'
                            : 'bg-[#12141c]/90 border border-neutral-800/80 rounded-tl-sm text-neutral-200 shadow-md backdrop-blur-md'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{m.text || (targetAction ? `Action Proposed: ${targetAction.tool_name}` : '')}</p>

                        {/* Action Card */}
                        {targetAction && (
                          <div className={`relative mt-4 p-4 rounded-xl bg-[#0b0d13] border shadow-xl space-y-3 overflow-hidden text-left ${
                            isHealing
                              ? 'border-emerald-500/40 shadow-emerald-950/20' 
                              : 'border-amber-500/40 shadow-amber-950/20'
                          }`}>
                            <div className={`flex items-center gap-2 font-semibold text-xs tracking-wider ${
                              isHealing ? 'text-emerald-400' : 'text-amber-400'
                            }`}>
                              {isHealing ? (
                                <><Wrench size={15} /> SELF-HEALING REPAIR PATCH</>
                              ) : (
                                <><ShieldAlert size={15} /> ACTION APPROVAL REQUIRED</>
                              )}
                            </div>

                            <div className="text-xs font-mono bg-black/60 p-3 rounded-lg border border-neutral-800 text-neutral-300 space-y-1">
                              <div className="text-neutral-400 font-sans">
                                Target Tool: <span className="text-emerald-400 font-mono font-semibold">{targetAction.tool_name}</span>
                              </div>
                              <pre className="text-[11px] text-neutral-300 overflow-x-auto pt-1 font-mono max-h-48">
                                {JSON.stringify(targetAction.arguments, null, 2)}
                              </pre>
                            </div>

                            {activeAction && activeAction.action_id === targetAction.action_id && (
                              <div className="flex items-center gap-2.5 pt-1">
                                <button
                                  onClick={() => handleApproval(activeAction.action_id, true)}
                                  className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-medium transition cursor-pointer shadow-md shadow-emerald-950/50"
                                >
                                  <CheckCircle2 size={13} /> Approve Action
                                </button>
                                <button
                                  onClick={() => handleApproval(activeAction.action_id, false)}
                                  className="flex items-center gap-1.5 px-4 py-2 bg-neutral-800/80 hover:bg-neutral-700/80 text-neutral-300 rounded-xl text-xs font-medium transition cursor-pointer border border-neutral-700/50"
                                >
                                  <XCircle size={13} /> Reject
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {m.sender === 'user' && (
                        <div className="h-8 w-8 rounded-xl bg-neutral-900 border border-neutral-800 flex items-center justify-center shrink-0 mt-0.5 text-neutral-400 shadow-md">
                          <User size={15} />
                        </div>
                      )}
                    </div>
                  );
                })}

                {loading && (
                  <div className="flex items-center gap-2.5 text-xs text-neutral-500 font-mono pl-11">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span>
                    qwen3-4b is processing...
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>
            </div>

            {/* Bottom Command Bar */}
            <div className="shrink-0 border-t border-neutral-800/60 bg-[#07080c]/90 backdrop-blur-2xl p-4 md:px-8">
              <form
                onSubmit={handleSend}
                className="max-w-4xl mx-auto flex items-end gap-2 bg-[#12141c] border border-neutral-800 focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/20 rounded-2xl p-2.5 transition shadow-2xl"
              >
                {/* Offline Microphone Button */}
                <button
                  type="button"
                  onClick={toggleSpeech}
                  title={isListening ? "Listening... (Click to stop)" : "Voice input (Click to speak)"}
                  className={`p-2.5 rounded-xl transition cursor-pointer shrink-0 ${
                    isListening 
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse' 
                      : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/80'
                  }`}
                >
                  {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                </button>

                <textarea
                  rows={1}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isListening ? "Listening to your voice..." : "Ask a question or enter a command... (Enter to send, Shift+Enter for newline)"}
                  className="flex-1 bg-transparent border-0 px-3 py-1.5 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none resize-none max-h-32"
                />

                <button
                  id="apex-send-btn"
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="p-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:from-neutral-800 disabled:to-neutral-800 disabled:text-neutral-600 text-white rounded-xl transition cursor-pointer shrink-0 shadow-md shadow-emerald-950/40"
                >
                  {loading ? <CornerDownLeft size={16} className="opacity-50" /> : <Send size={16} />}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Tab 2: Tasks & Goals */}
        {activeTab === 'tasks' && (
          <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-neutral-100">Tasks & Study Goals</h2>
              <p className="text-xs text-neutral-500">Persistent workspace checklist stored locally in SQLite.</p>
            </div>

            <form onSubmit={handleCreateTask} className="flex gap-2">
              <input
                type="text"
                value={newTaskInput}
                onChange={(e) => setNewTaskInput(e.target.value)}
                placeholder="Add a new milestone or task..."
                className="flex-1 bg-[#12141c] border border-neutral-800 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500/40 text-neutral-200"
              />
              <button
                type="submit"
                className="px-4.5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-sm font-medium flex items-center gap-1.5 cursor-pointer shadow-md shadow-emerald-950/40"
              >
                <Plus size={16} /> Add Task
              </button>
            </form>

            <div className="space-y-2.5">
              {tasks.length === 0 ? (
                <div className="p-8 text-center text-xs text-neutral-600 border border-dashed border-neutral-800/80 rounded-2xl">
                  No tasks active. Add your first goal above.
                </div>
              ) : (
                tasks.map(t => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between p-3.5 bg-[#12141c]/80 border border-neutral-800/80 rounded-xl hover:border-neutral-700/60 transition shadow-sm"
                  >
                    <div
                      onClick={() => handleToggleTask(t.id)}
                      className="flex items-center gap-3 cursor-pointer flex-1"
                    >
                      {t.completed ? (
                        <CheckSquare size={18} className="text-emerald-400 shrink-0" />
                      ) : (
                        <Square size={18} className="text-neutral-500 shrink-0" />
                      )}
                      <span className={`text-sm ${t.completed ? 'line-through text-neutral-500' : 'text-neutral-200'}`}>
                        {t.title}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteTask(t.id)}
                      className="text-neutral-600 hover:text-red-400 p-1.5 rounded transition cursor-pointer"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 3: System Logs */}
        {activeTab === 'logs' && (
          <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-neutral-100 flex items-center gap-2">
                  <Activity size={18} className="text-emerald-400" /> System Action Audit Logs
                </h2>
                <p className="text-xs text-neutral-500">Immutable ledger of every executed tool call and user decision.</p>
              </div>
              <button
                onClick={loadLogs}
                className="text-xs bg-[#12141c] border border-neutral-800 px-3 py-1.5 rounded-lg text-neutral-300 hover:text-white cursor-pointer"
              >
                Refresh Logs
              </button>
            </div>

            <div className="border border-neutral-800/80 rounded-2xl overflow-hidden bg-[#12141c]/50 backdrop-blur-md">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-900/60 text-neutral-400 border-b border-neutral-800/80">
                  <tr>
                    <th className="p-3 font-medium">Timestamp</th>
                    <th className="p-3 font-medium">Tool Call</th>
                    <th className="p-3 font-medium">Parameters</th>
                    <th className="p-3 font-medium">Audit Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60 font-mono text-[11px]">
                  {logs.map(log => (
                    <tr key={log.id} className="hover:bg-neutral-800/20">
                      <td className="p-3 text-neutral-500 whitespace-nowrap">{log.timestamp}</td>
                      <td className="p-3 text-emerald-400 font-semibold">{log.tool_name}</td>
                      <td className="p-3 text-neutral-400 max-w-xs truncate" title={log.arguments}>{log.arguments}</td>
                      <td className="p-3">
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] uppercase font-sans font-medium ${
                          log.status === 'approved' || log.status === 'auto_executed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}