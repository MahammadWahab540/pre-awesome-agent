/**
 * Client-Side Debug Logger for ADK Audio Streaming
 * Logs all audio worklet, WebSocket, and streaming events for debugging
 */

export class ClientDebugLogger {
  private sessionId: string;
  private logs: string[] = [];
  private maxLogs: number = 1000;
  private stats = {
    audioChunksSent: 0,
    audioChunksReceived: 0,
    textMessagesSent: 0,
    textMessagesReceived: 0,
    interruptions: 0,
    turnCompletions: 0,
    errors: 0,
    bytesSent: 0,
    bytesReceived: 0,
  };

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.log('INFO', '🚀 Client Debug Logger Initialized', { sessionId });
  }

  private log(level: string, message: string, data?: any) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level}] ${message}`;
    
    console.log(`%c${logEntry}`, this.getColorForLevel(level), data || '');
    
    this.logs.push(logEntry + (data ? ` | ${JSON.stringify(data)}` : ''));
    
    // Trim logs if too many
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }
  }

  private getColorForLevel(level: string): string {
    switch (level) {
      case 'ERROR': return 'color: red; font-weight: bold';
      case 'WARN': return 'color: orange; font-weight: bold';
      case 'INFO': return 'color: blue';
      case 'DEBUG': return 'color: gray';
      default: return '';
    }
  }

  logWebSocketConnected(isAudio: boolean) {
    this.log('INFO', '🔌 WebSocket CONNECTED', { isAudio, url: window.location.href });
  }

  logWebSocketDisconnected() {
    this.log('INFO', '🔌 WebSocket DISCONNECTED');
    // Log stats to console but don't auto-download (removed automatic download)
    this.logStats();
    // Log summary to console for debugging (no file download)
    const summary = {
      sessionId: this.sessionId,
      timestamp: new Date().toISOString(),
      stats: this.stats,
      logCount: this.logs.length,
    };
    console.log('%c=== SESSION SUMMARY ===', 'color: purple; font-size: 16px; font-weight: bold');
    console.log(JSON.stringify(summary, null, 2));
    console.log('%c=====================', 'color: purple; font-size: 16px; font-weight: bold');
  }

  logWebSocketError(error: any) {
    this.stats.errors++;
    this.log('ERROR', '❌ WebSocket ERROR', { error: error.toString() });
  }

  logWebSocketMessage(direction: 'SEND' | 'RECEIVE', mimeType: string, dataPreview?: string) {
    const arrow = direction === 'SEND' ? '→' : '←';
    this.log('DEBUG', `🌐 WS ${direction} ${arrow}`, { mimeType, preview: dataPreview });
  }

  logAudioWorkletInitialized(type: 'player' | 'recorder') {
    this.log('INFO', `🎵 Audio Worklet INITIALIZED: ${type}`);
  }

  logAudioChunkSent(size: number) {
    this.stats.audioChunksSent++;
    this.stats.bytesSent += size;
    this.log('DEBUG', `🎤 Audio Chunk SENT #${this.stats.audioChunksSent}`, { 
      size, 
      totalSent: this.stats.bytesSent 
    });
  }

  logAudioChunkReceived(size: number) {
    this.stats.audioChunksReceived++;
    this.stats.bytesReceived += size;
    this.log('DEBUG', `🔊 Audio Chunk RECEIVED #${this.stats.audioChunksReceived}`, { 
      size, 
      totalReceived: this.stats.bytesReceived 
    });
  }

  logTextSent(text: string) {
    this.stats.textMessagesSent++;
    const preview = text.substring(0, 100) + (text.length > 100 ? '...' : '');
    this.log('INFO', `💬 Text SENT #${this.stats.textMessagesSent}`, { preview });
  }

  logTextReceived(text: string, isPartial: boolean) {
    if (!isPartial) {
      this.stats.textMessagesReceived++;
    }
    const preview = text.substring(0, 100) + (text.length > 100 ? '...' : '');
    this.log('INFO', `💬 Text RECEIVED ${isPartial ? '(PARTIAL)' : '(COMPLETE)'}`, { preview });
  }

  logTurnComplete() {
    this.stats.turnCompletions++;
    this.log('INFO', `✅ Turn COMPLETE #${this.stats.turnCompletions}`);
  }

  logInterruption() {
    this.stats.interruptions++;
    this.log('WARN', `⚠️ INTERRUPTION DETECTED #${this.stats.interruptions}`);
  }

  logAudioBufferCleared(reason: string) {
    this.log('WARN', '🔇 Audio Buffer CLEARED', { reason });
  }

  logError(context: string, error: any) {
    this.stats.errors++;
    this.log('ERROR', `❌ ERROR in ${context}`, { 
      error: error.toString(), 
      stack: error.stack 
    });
  }

  logADKCompliance(check: string, passed: boolean, details?: string) {
    const status = passed ? '✅ PASS' : '❌ FAIL';
    this.log('INFO', `🔍 ADK COMPLIANCE: ${status} - ${check}`, { details });
  }

  logStats() {
    this.log('INFO', '📊 SESSION STATISTICS', this.stats);
  }

  exportLogs(autoDownload: boolean = false): string {
    const exportData = {
      sessionId: this.sessionId,
      timestamp: new Date().toISOString(),
      stats: this.stats,
      logs: this.logs,
    };
    
    const dataStr = JSON.stringify(exportData, null, 2);
    
    // Log to console for easy copying
    console.log('%c=== CLIENT DEBUG LOGS ===', 'color: purple; font-size: 16px; font-weight: bold');
    console.log(dataStr);
    console.log('%c=====================', 'color: purple; font-size: 16px; font-weight: bold');
    
    // Only download if explicitly requested (removed automatic download)
    if (autoDownload) {
      try {
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `client-debug-${this.sessionId}-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.log('INFO', '📥 Debug logs exported to file');
      } catch (error) {
        this.log('ERROR', 'Failed to export logs', { error });
      }
    }
    
    return dataStr;
  }

  getLogs(): string[] {
    return [...this.logs];
  }

  getStats() {
    return { ...this.stats };
  }
}

// Singleton instance for easy access
let debugLogger: ClientDebugLogger | null = null;

export function initializeClientDebugLogger(sessionId: string): ClientDebugLogger {
  debugLogger = new ClientDebugLogger(sessionId);
  
  // Make it globally accessible for debugging
  (window as any).adkDebugLogger = debugLogger;
  
  console.log('%c🔧 ADK Debug Logger Ready', 'color: green; font-size: 14px; font-weight: bold');
  console.log('Access via: window.adkDebugLogger');
  console.log('Commands:');
  console.log('  window.adkDebugLogger.logStats() - View statistics');
  console.log('  window.adkDebugLogger.exportLogs(true) - Download logs as file');
  console.log('  window.adkDebugLogger.exportLogs() - View logs in console (no download)');
  
  return debugLogger;
}

export function getClientDebugLogger(): ClientDebugLogger | null {
  return debugLogger;
}
