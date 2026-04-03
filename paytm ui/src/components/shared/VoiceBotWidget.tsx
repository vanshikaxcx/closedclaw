'use client';

import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  Keyboard,
  Loader2,
  MessageCircle,
  Mic,
  Send,
  Trash2,
  User,
  Volume2,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { cn } from '@/lib/utils';
import { adapter } from '@/src/adapters';
import { useAppToast } from '@/src/components/ui';

interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  text: string;
  audioBase64?: string | null;
  autoplayBlocked?: boolean;
}

type InputMode = 'voice' | 'text';

const LIVE_API_NOTICE = 'Live API feature — works in all modes';

function renderInlineMarkdown(line: string): Array<string | ReactNode> {
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={`strong_${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function MarkdownBubble({ text }: { text: string }) {
  const lines = text.split('\n');
  const blocks: ReactNode[] = [];
  let listBuffer: string[] = [];

  const flushList = () => {
    if (!listBuffer.length) {
      return;
    }

    blocks.push(
      <ul key={`list_${blocks.length}`} className="list-disc space-y-1 pl-4">
        {listBuffer.map((item, index) => (
          <li key={`li_${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>,
    );

    listBuffer = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listBuffer.push(trimmed.slice(2));
      continue;
    }

    flushList();

    if (!trimmed) {
      blocks.push(<div key={`spacer_${blocks.length}`} className="h-1" />);
      continue;
    }

    blocks.push(
      <p key={`p_${blocks.length}`} className="text-sm leading-relaxed">
        {renderInlineMarkdown(trimmed)}
      </p>,
    );
  }

  flushList();

  return <div className="space-y-1 text-sm text-slate-800">{blocks}</div>;
}

function randomId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function VoiceBotWidget() {
  const { isDemoMode } = useAuth();
  const { showToast } = useAppToast();

  const [isOpen, setIsOpen] = useState(false);
  const [inputMode, setInputMode] = useState<InputMode>('voice');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [textQuery, setTextQuery] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [inlineNotice, setInlineNotice] = useState<string | null>(null);
  const [mediaSupported, setMediaSupported] = useState(true);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const conversationRef = useRef<HTMLDivElement | null>(null);

  const canUseVoiceMode = useMemo(() => mediaSupported && typeof window !== 'undefined', [mediaSupported]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const supported = 'MediaRecorder' in window && !!navigator.mediaDevices?.getUserMedia;
    setMediaSupported(supported);
    if (!supported) {
      setInputMode('text');
      setInlineNotice('Microphone is unavailable in this browser. Switched to text mode.');
    }
  }, []);

  useEffect(() => {
    const node = conversationRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages, isProcessing]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const openHandler = () => setIsOpen(true);
    window.addEventListener('arthsetu:open-voicebot', openHandler);
    return () => {
      window.removeEventListener('arthsetu:open-voicebot', openHandler);
    };
  }, []);

  useEffect(() => {
    return () => {
      try {
        recorderRef.current?.stop();
      } catch {
        // no-op
      }
      if (streamRef.current) {
        for (const track of streamRef.current.getTracks()) {
          track.stop();
        }
      }
    };
  }, []);

  const notifyLiveApi = () => {
    if (isDemoMode) {
      showToast({ title: LIVE_API_NOTICE, variant: 'warning' });
    }
  };

  const playAudio = async (audioBase64: string | null | undefined): Promise<void> => {
    if (!audioBase64) {
      return;
    }

    const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
    await audio.play();
  };

  const setAutoplayBlocked = (messageId: string) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId
          ? {
              ...message,
              autoplayBlocked: true,
            }
          : message,
      ),
    );
  };

  const releaseStream = () => {
    if (!streamRef.current) {
      return;
    }

    for (const track of streamRef.current.getTracks()) {
      track.stop();
    }
    streamRef.current = null;
  };

  const processRecordedAudio = async () => {
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    chunksRef.current = [];
    setIsRecording(false);
    releaseStream();

    if (!blob.size) {
      showToast({ title: 'Audio capture failed', description: 'No audio was recorded.', variant: 'error' });
      return;
    }

    if (!adapter.sendGstVoiceAudio) {
      showToast({ title: 'Voice endpoint unavailable', variant: 'error' });
      return;
    }

    notifyLiveApi();
    setIsProcessing(true);

    try {
      const payload = await adapter.sendGstVoiceAudio(blob, `gst_voice_${Date.now()}.webm`);

      const userMessage: ChatMessage = {
        id: randomId('user_voice'),
        role: 'user',
        text: payload.transcription || 'Voice query submitted.',
      };

      const botMessageId = randomId('bot_voice');
      const botMessage: ChatMessage = {
        id: botMessageId,
        role: 'bot',
        text: payload.responseText,
        audioBase64: payload.audioBase64,
      };

      setMessages((current) => [...current, userMessage, botMessage]);

      if (payload.audioBase64) {
        try {
          await playAudio(payload.audioBase64);
        } catch {
          setAutoplayBlocked(botMessageId);
        }
      }
    } catch (error) {
      showToast({
        title: 'Voice request failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const startRecording = async () => {
    if (!canUseVoiceMode) {
      setInputMode('text');
      setInlineNotice('Microphone is unavailable in this browser. Switched to text mode.');
      return;
    }

    if (isProcessing || isRecording) {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const preferredMime =
        typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : undefined;

      const recorder = preferredMime ? new MediaRecorder(stream, { mimeType: preferredMime }) : new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        void processRecordedAudio();
      };

      recorder.start();
      setInlineNotice(null);
      setIsRecording(true);
    } catch {
      setInputMode('text');
      setInlineNotice('Microphone permission denied. Switched to text mode.');
    }
  };

  const stopRecording = () => {
    if (!isRecording) {
      return;
    }

    try {
      recorderRef.current?.stop();
    } catch {
      setIsRecording(false);
      releaseStream();
      showToast({ title: 'Unable to stop recording', variant: 'error' });
    }
  };

  const sendTextQuery = async () => {
    const query = textQuery.trim();
    if (!query || isProcessing) {
      return;
    }

    if (!adapter.sendGstVoiceText) {
      showToast({ title: 'Text voice endpoint unavailable', variant: 'error' });
      return;
    }

    notifyLiveApi();
    const userMessage: ChatMessage = { id: randomId('user_text'), role: 'user', text: query };
    setMessages((current) => [...current, userMessage]);
    setTextQuery('');
    setIsProcessing(true);

    try {
      const payload = await adapter.sendGstVoiceText(query);
      const botMessage: ChatMessage = { id: randomId('bot_text'), role: 'bot', text: payload.responseText };
      setMessages((current) => [...current, botMessage]);
    } catch (error) {
      showToast({
        title: 'Text query failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setInlineNotice(null);
  };

  const switchToVoice = () => {
    if (!canUseVoiceMode) {
      setInputMode('text');
      setInlineNotice('Microphone is unavailable in this browser. Switched to text mode.');
      return;
    }

    setInputMode('voice');
    setInlineNotice(null);
  };

  return (
    <>
      {!isOpen ? (
        <button
          type="button"
          className="fixed bottom-24 right-4 z-88 inline-flex items-center gap-2 rounded-full bg-[#002970] px-4 py-3 text-sm font-bold text-white shadow-[0_14px_28px_rgba(2,41,112,0.35)] transition hover:bg-[#0a3f9d] lg:bottom-6"
          onClick={() => setIsOpen(true)}
        >
          <MessageCircle size={18} />
          GST VoiceBot
        </button>
      ) : null}

      {isOpen ? (
        <section className="fixed bottom-24 right-3 z-95 flex h-[min(80vh,560px)] w-[min(80vw,360px)] flex-col overflow-hidden rounded-3xl border border-[#d7e0f0] bg-white shadow-[0_18px_44px_rgba(2,41,112,0.22)] lg:bottom-6">
          <header className="flex items-center justify-between border-b border-[#e4eaf6] bg-[#f8fbff] px-4 py-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">Tax Assistant</p>
              <h3 className="text-sm font-black text-[#002970]">ArthSetu VoiceBot — your GST expert.</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                onClick={clearConversation}
                aria-label="Clear conversation"
              >
                <Trash2 size={15} />
              </button>
              <button
                type="button"
                className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                onClick={() => setIsOpen(false)}
                aria-label="Close widget"
              >
                <X size={16} />
              </button>
            </div>
          </header>

          <div className="border-b border-[#e4eaf6] px-3 py-2">
            <div className="inline-flex rounded-full border border-[#d2dced] bg-white p-1">
              <button
                type="button"
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition',
                  inputMode === 'voice' ? 'bg-[#002970] text-white' : 'text-slate-600 hover:bg-[#eef5ff]',
                )}
                onClick={switchToVoice}
              >
                <Mic size={13} />
                Voice
              </button>
              <button
                type="button"
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition',
                  inputMode === 'text' ? 'bg-[#002970] text-white' : 'text-slate-600 hover:bg-[#eef5ff]',
                )}
                onClick={() => setInputMode('text')}
              >
                <Keyboard size={13} />
                Text
              </button>
            </div>
            {inlineNotice ? <p className="mt-2 text-xs font-semibold text-[#a16207]">{inlineNotice}</p> : null}
          </div>

          <div ref={conversationRef} className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {messages.length === 0 ? (
              <div className="paytm-surface p-3 text-sm text-slate-600">
                Ask GST questions by voice or text, and get instant guidance with practical next actions.
              </div>
            ) : null}

            {messages.map((message) => (
              <article
                key={message.id}
                className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[88%] rounded-2xl px-3 py-2',
                    message.role === 'user' ? 'bg-[#002970] text-white' : 'border border-[#e2e9f4] bg-white',
                  )}
                >
                  <p className="mb-1 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.12em] text-current/80">
                    {message.role === 'user' ? <User size={11} /> : <Bot size={11} />}
                    {message.role === 'user' ? 'You' : 'VoiceBot'}
                  </p>

                  {message.role === 'bot' ? <MarkdownBubble text={message.text} /> : <p className="text-sm">{message.text}</p>}

                  {message.role === 'bot' && message.audioBase64 && message.autoplayBlocked ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="mt-2 h-8 rounded-full"
                      onClick={() => {
                        void playAudio(message.audioBase64).catch(() => {
                          showToast({ title: 'Unable to play audio response', variant: 'error' });
                        });
                      }}
                    >
                      <Volume2 size={14} />
                      Play
                    </Button>
                  ) : null}
                </div>
              </article>
            ))}

            {isProcessing ? (
              <article className="flex justify-start">
                <div className="inline-flex items-center gap-2 rounded-2xl border border-[#e2e9f4] bg-white px-3 py-2 text-sm text-slate-700">
                  <Loader2 size={14} className="animate-spin" />
                  Processing...
                </div>
              </article>
            ) : null}
          </div>

          <footer className="border-t border-[#e4eaf6] px-3 py-3">
            {inputMode === 'voice' ? (
              <div className="flex flex-col items-center gap-2">
                <button
                  type="button"
                  className={cn(
                    'relative inline-flex h-14 w-14 items-center justify-center rounded-full text-white shadow',
                    isRecording ? 'animate-pulse bg-[#dc2626]' : 'bg-[#002970] hover:bg-[#0a3f9d]',
                  )}
                  onClick={isRecording ? stopRecording : () => void startRecording()}
                  disabled={isProcessing}
                >
                  <Mic size={20} />
                </button>
                <p className="text-xs font-semibold text-slate-600">
                  {isRecording ? 'Recording... tap to stop' : 'Tap to record GST question'}
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  value={textQuery}
                  onChange={(event) => setTextQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      void sendTextQuery();
                    }
                  }}
                  placeholder="Ask your GST question"
                  className="h-10 flex-1 rounded-xl border border-[#d2dced] px-3 text-sm outline-none focus:border-[#0a58d8]"
                />
                <Button
                  type="button"
                  className="h-10 rounded-xl bg-[#002970] px-3 hover:bg-[#0a3f9d]"
                  onClick={() => void sendTextQuery()}
                  disabled={isProcessing || !textQuery.trim()}
                >
                  <Send size={15} />
                </Button>
              </div>
            )}
          </footer>
        </section>
      ) : null}
    </>
  );
}
