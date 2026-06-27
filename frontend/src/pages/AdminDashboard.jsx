import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { CheckCircle2, AlertTriangle, FileText, Activity, UploadCloud, Loader2, RefreshCw, Download } from 'lucide-react';
import { API_BASE_URL } from '../config';

export default function AdminDashboard() {
  const [anomalies, setAnomalies] = useState([]);
  const [stats, setStats] = useState({
    processed: 0,
    automationScore: 0,
    inQueue: 0,
    activeClinics: 0
  });
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isLive, setIsLive] = useState(false);
  
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('fast_track');
  const [queueCounts, setQueueCounts] = useState({ fast_track: 0, anomaly: 0 });
  const [lastProcessingCount, setLastProcessingCount] = useState(0);
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchAnomalies(activeTab);
    fetchStats();

    // Poll stats every 5 seconds
    const statsInterval = setInterval(() => {
      fetchStats();
    }, 5000);

    // Poll anomaly queue every 10 seconds
    const anomalyInterval = setInterval(() => {
      fetchAnomalies(activeTab);
    }, 10000);

    return () => {
      clearInterval(statsInterval);
      clearInterval(anomalyInterval);
    };
  }, [activeTab]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/admin/stats`);
      const newStats = response.data;
      setStats(newStats);
      setLastUpdated(new Date());
      setIsLive(true);
      
      const currentProcessing = newStats.processingCount || 0;
      setLastProcessingCount(prev => {
        if (prev > 0 && currentProcessing === 0) {
          setShowSuccessToast(true);
          setTimeout(() => setShowSuccessToast(false), 8000);
          fetchAnomalies(activeTab);
        }
        return currentProcessing;
      });
    } catch (error) {
      console.error("Ошибка при загрузке статистики:", error);
      setIsLive(false);
    }
  };

  const fetchAnomalies = async (tab = activeTab) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/admin/unmatched?queue=${tab}`);
      setAnomalies(response.data.items || []);
      setQueueCounts({
        fast_track: response.data.fast_track_count || 0,
        anomaly: response.data.anomaly_count || 0
      });
    } catch (error) {
      console.error("Ошибка при загрузке аномалий:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.zip')) {
      setUploadMessage('Ошибка: Пожалуйста, загрузите ZIP-архив.');
      return;
    }

    setUploading(true);
    setUploadMessage('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/admin/upload-prices`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setUploadMessage(`Успешно: ${response.data.message}`);
      // В реальном приложении здесь можно запустить поллинг или WebSockets
      setTimeout(() => {
        fetchAnomalies();
        fetchStats();
      }, 5000); 
    } catch (error) {
      setUploadMessage(`Ошибка: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRowChange = (id, field, value) => {
    setAnomalies(prev => prev.map(a => a.id === id ? { ...a, [field]: value } : a));
  };

  const handleApprove = async (id, serviceId, newPrice, newPriceNonresident, rawName, serviceName = null) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('raw_name', rawName);
      if (serviceId !== null && serviceId !== undefined && !isNaN(serviceId)) {
        params.append('service_id', serviceId);
      }
      if (serviceName) {
        params.append('service_name', serviceName);
      }
      if (newPrice !== null && newPrice !== undefined && !isNaN(newPrice)) {
        params.append('price', newPrice);
      }
      if (newPriceNonresident !== null && newPriceNonresident !== undefined && !isNaN(newPriceNonresident)) {
        params.append('price_nonresident', newPriceNonresident);
      }

      const response = await axios.post(`${API_BASE_URL}/api/v1/admin/match/${id}?${params.toString()}`);
      if (response.status === 200) {
        setAnomalies(prev => prev.filter(a => a.id !== id));
        setQueueCounts(prev => ({ ...prev, [activeTab]: Math.max(0, prev[activeTab] - 1) }));
        fetchStats();
      }
    } catch (error) {
      console.error("Ошибка при подтверждении:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async (id) => {
    setLoading(true);
    try {
      const response = await axios.delete(`${API_BASE_URL}/api/v1/admin/reject/${id}`);
      if (response.status === 200) {
        setAnomalies(prev => prev.filter(a => a.id !== id));
        setQueueCounts(prev => ({ ...prev, [activeTab]: Math.max(0, prev[activeTab] - 1) }));
        fetchStats();
      }
    } catch (error) {
      console.error("Ошибка при отклонении:", error);
    } finally {
      setLoading(false);
    }
  };

  const displayedItems = anomalies;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#111827]">Панель оператора</h1>
        <p className="text-[#6B7280] mt-1">Аналитика, верификация парсинга и управление справочником</p>
      </div>

      {showSuccessToast && (
        <div className="bg-[#E6F4EA] border border-[#137333] text-[#137333] px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 font-medium">
            <CheckCircle2 className="w-5 h-5 text-[#10B981]" />
            <span>Все файлы успешно обработаны и сопоставлены! Очередь обновлена.</span>
          </div>
          <button 
            onClick={() => setShowSuccessToast(false)} 
            className="text-[#137333] hover:text-[#0b4d20] font-bold text-sm cursor-pointer ml-4"
          >
            ✕
          </button>
        </div>
      )}
      
      {stats.processingCount > 0 && (
        <div className="bg-[#E8F0FE] border border-[#1A73E8] text-[#1A73E8] px-4 py-3 flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-[#1A73E8]" />
          <span className="font-medium">Идет фоновое распознавание и сопоставление файлов... Осталось: <span className="font-bold">{stats.processingCount}</span></span>
        </div>
      )}

      {/* Upload Zone */}
      <div className="bg-white border border-[#E5E7EB] p-8 flex flex-col items-center justify-center relative">
        <UploadCloud className="w-12 h-12 text-[#9CA3AF] mb-4" />
        <h3 className="text-lg font-medium text-[#111827] mb-1">Загрузить архив прайс-листов</h3>
        <p className="text-sm text-[#6B7280] mb-6">Поддерживаются только .zip архивы (содержащие PDF, DOCX, XLSX)</p>
        
        <div className="flex items-center gap-4 mb-6">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-[#374151]">Курс валют будет рассчитан автоматически (по году прайса)</label>
          </div>
        </div>

        <input 
          type="file" 
          accept=".zip" 
          ref={fileInputRef}
          onChange={handleFileUpload}
          className="hidden" 
        />
        
        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-6 py-2.5 font-medium flex items-center gap-2"
        >
          {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Обработка...</> : 'Выбрать ZIP-архив'}
        </button>
        
        {uploadMessage && (
          <div className={`mt-4 text-sm font-medium ${uploadMessage.startsWith('Ошибка') ? 'text-[#DC2626]' : 'text-[#059669]'}`}>
            {uploadMessage}
          </div>
        )}
      </div>

      {/* Dashboard Widgets */}
      <div className="flex justify-between items-end mb-4">
          <div className="text-xs text-[#9CA3AF]">
            <span className={`font-semibold ${isLive ? 'text-[#059669]' : 'text-[#9CA3AF]'}`}>{isLive ? 'В реальном времени' : 'Нет соединения'}</span>
            {lastUpdated && <span className="ml-2">Обновлено: {lastUpdated.toLocaleTimeString('ru-RU')}</span>}
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                window.open(`${API_BASE_URL}/api/v1/admin/export`, '_blank');
              }}
              className="flex items-center gap-1.5 text-xs font-medium text-[#111827] bg-white border border-[#D1D5DB] px-3 py-1.5 hover:bg-[#F9FAFB] cursor-pointer"
            >
              <Download size={14} /> Экспорт (CSV)
            </button>
            <button 
              onClick={() => { fetchStats(); fetchAnomalies(activeTab); }}
              className="flex items-center gap-1 text-xs font-medium text-[#6B7280] hover:text-[#111827] cursor-pointer"
            >
              <RefreshCw size={14} /> Обновить
            </button>
          </div>
        </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-[#E5E7EB] p-6">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <FileText size={20} />
            <h3 className="font-medium text-sm">Обработано прайсов</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827] tabular-nums">{stats.processed}</div>
          <div className="text-[11px] text-[#9CA3AF] mt-1">документов распознано</div>
        </div>
        
        <div className="bg-white border border-[#E5E7EB] p-6">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <CheckCircle2 size={20} />
            <h3 className="font-medium text-sm">Автонормализация</h3>
          </div>
          <div className="flex items-end gap-2">
            <div className="text-3xl font-bold text-[#059669] tabular-nums">{stats.automationScore}%</div>
            <span className="text-xs text-[#6B7280] mb-1">цель: 70%</span>
          </div>
          <div className="w-full bg-[#F3F4F6] h-1.5 -full mt-3 overflow-hidden">
            <div className="bg-[#059669] h-full -full" style={{ width: `${Math.min(stats.automationScore, 100)}%` }}></div>
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <AlertTriangle size={20} />
            <h3 className="font-medium text-sm">В очереди (Аномалии)</h3>
          </div>
          <div className="text-3xl font-bold text-[#DC2626] tabular-nums">{stats.inQueue.toLocaleString('ru-RU')}</div>
          <div className="text-[11px] text-[#9CA3AF] mt-1">ждут верификации оператора</div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <Activity size={20} />
            <h3 className="font-medium text-sm">Активных клиник</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827] tabular-nums">{stats.activeClinics}</div>
          <div className="text-[11px] text-[#9CA3AF] mt-1">с актуальными прайсами</div>
        </div>
      </div>

      {/* Verification Queue (Split Screen) */}
      <div>
        <h2 className="text-lg font-bold text-[#111827] mb-4">Очередь верификации</h2>
        
        {/* Tab Buttons */}
        <div className="flex border-b border-[#E5E7EB] mb-6 gap-6">
          <button
            onClick={() => setActiveTab('fast_track')}
            className={`pb-3 text-sm font-semibold relative cursor-pointer flex items-center ${
 activeTab === 'fast_track' ? 'text-[#059669]' : 'text-[#6B7280] hover:text-[#111827]'
 }`}
          >
            Доверяемые услуги (Зеленая очередь)
            <span className="ml-2 bg-[#E6F4EA] text-[#059669] text-xs px-2 py-0.5 -full font-semibold">
              {queueCounts.fast_track}
            </span>
            {activeTab === 'fast_track' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#059669]" />
            )}
          </button>
          
          <button
            onClick={() => setActiveTab('anomaly')}
            className={`pb-3 text-sm font-semibold relative cursor-pointer flex items-center ${
 activeTab === 'anomaly' ? 'text-[#DC2626]' : 'text-[#6B7280] hover:text-[#111827]'
 }`}
          >
            Сомнительные / Аномалии
            <span className="ml-2 bg-[#FCE8E6] text-[#C5221F] text-xs px-2 py-0.5 -full font-semibold">
              {queueCounts.anomaly}
            </span>
            {activeTab === 'anomaly' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#DC2626]" />
            )}
          </button>
        </div>

        {displayedItems.length === 0 ? (
          <div className="text-center py-12 bg-white border border-[#E5E7EB]">
            <CheckCircle2 className="mx-auto h-12 w-12 text-[#D1D5DB] mb-3" />
            <h3 className="text-sm font-medium text-[#374151]">Очередь пуста</h3>
            <p className="text-sm text-[#6B7280] mt-1">
              {activeTab === 'fast_track' 
                ? 'Нет доверяемых услуг с высокой уверенностью сопоставления.' 
                : 'Нет сомнительных услуг или аномалий.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {displayedItems.map((item) => (
              <div 
                key={item.id}
                className={`border overflow-hidden ${item.status === 'anomaly' ? 'border-[#FBBF24] bg-[#FEFCE8]' : item.status === 'fast_track' ? 'border-[#10B981] bg-[#F0FDF4]' : 'border-[#E5E7EB] bg-white'}`}
              >
                {/* Clinic & File Header Info */}
                <div className="bg-[#F9FAFB] border-b border-[#E5E7EB] px-5 py-2 flex justify-between items-center text-xs text-[#4B5563]">
                  <div className="font-semibold flex items-center gap-1">
                    <span className="text-[#9CA3AF]">Клиника:</span> {item.partner_name || 'Неизвестная клиника'}
                  </div>
                  <div className="text-[#6B7280]">
                    <span className="text-[#9CA3AF]">Файл:</span> {item.file_name || 'Неизвестный файл'}
                  </div>
                </div>
                
                {item.note && (
                  <div className={`border-b px-5 py-2 text-xs font-medium flex items-center gap-2 ${
 item.status === 'anomaly' ? 'bg-[#FEFCE8] border-[#FBBF24] text-[#B45309]' : 
 item.status === 'fast_track' ? 'bg-[#ECFDF5] border-[#10B981] text-[#047857]' : 
 'bg-[#F3F4F6] border-[#D1D5DB] text-[#4B5563]'
 }`}>
                    {item.status === 'fast_track' ? <CheckCircle2 size={14} className="text-[#10B981]" /> : <AlertTriangle size={14} className="text-[#FBBF24]" />}
                    {item.note}
                  </div>
                )}
                
                <div className="flex flex-col lg:flex-row">
                  {/* Source Block */}
                  <div className="flex-1 p-5 border-b lg:border-b-0 lg:border-r border-[#E5E7EB]">
                    <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider mb-2">Источник (Сырые данные)</div>
                    <input 
                      type="text" 
                      value={item.raw_name} 
                      onChange={e => handleRowChange(item.id, 'raw_name', e.target.value)}
                      className="font-medium text-[#111827] text-base mb-2 border border-[#D1D5DB] px-2 py-1 w-full focus:ring-[#2563EB] focus:outline-none"
                    />
                    <div className="flex flex-col gap-2 text-sm mt-4">
                      {item.old_price && (
                        <div className="text-[#6B7280] mb-2">Старая цена (Рез): <span className="line-through">{item.old_price} ₸</span></div>
                      )}
                      
                      {item.price_original !== undefined && item.price_original !== null && (
                        <div className="text-xs text-[#6B7280] mb-2 bg-[#F3F4F6] px-2 py-1 w-fit">
                          Цена в файле (Релиз): <span className="font-semibold">{item.price_original.toLocaleString('ru-RU')} {item.currency_original || 'KZT'}</span>
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <span className="w-24 text-[#6B7280]">Резидент:</span>
                        <div className="text-[#111827] font-semibold flex items-center">
                          <input 
                            type="number" 
                            value={item.new_price} 
                            onChange={e => handleRowChange(item.id, 'new_price', e.target.value)}
                            className="border border-[#D1D5DB] px-2 py-1 w-36 text-sm mr-2 focus:ring-[#2563EB] focus:outline-none"
                          /> ₸
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className="w-24 text-[#6B7280]">Нерезидент:</span>
                        <div className="text-[#111827] font-semibold flex items-center">
                          <input 
                            type="number" 
                            value={item.new_price_nonresident} 
                            onChange={e => handleRowChange(item.id, 'new_price_nonresident', e.target.value)}
                            className="border border-[#D1D5DB] px-2 py-1 w-36 text-sm mr-2 focus:ring-[#2563EB] focus:outline-none"
                          /> ₸
                        </div>
                      </div>

                      {item.old_price && (
                        <div className={`font-bold text-xs ${
 item.status === 'anomaly' || 
 Math.abs((parseFloat(item.new_price) - parseFloat(item.old_price)) / parseFloat(item.old_price)) > 0.5 
 ? 'text-[#DC2626]' 
 : 'text-[#6B7280]'
 }`}>
                          ({(() => {
                            const oldP = parseFloat(item.old_price);
                            const newP = parseFloat(item.new_price);
                            if (isNaN(oldP) || isNaN(newP) || oldP === 0) return '0%';
                            const diff = newP - oldP;
                            const diffPct = (diff / oldP) * 100;
                            const sign = diff > 0 ? "+" : "";
                            return `${sign}${Math.round(diffPct)}%`;
                          })()})
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Suggestion Block */}
                  <div className="flex-1 p-5 bg-white flex flex-col">
                    <div className="flex justify-between items-start mb-2">
                      <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Предложение ИИ</div>
                      {item.confidence !== undefined && item.confidence !== null && item.confidence > 0 && (
                        <div className="bg-[#ECFDF5] text-[#059669] px-2 py-0.5 text-[11px] font-medium">
                          Уверенность: {item.confidence}%
                        </div>
                      )}
                    </div>
                    <div className="font-medium text-[#2563EB] text-base mb-4">{item.suggested_service_name ? item.suggested_service_name : (item.suggested_service_id ? `Услуга ID: ${item.suggested_service_id}` : 'Не сопоставлено')}</div>
                    
                    <div className="flex gap-2 mt-auto">
                      <button 
                        onClick={() => {
                          handleApprove(item.id, item.suggested_service_id, parseFloat(item.new_price), parseFloat(item.new_price_nonresident), item.raw_name);
                        }}
                        disabled={loading}
                        className="bg-[#10B981] hover:bg-[#059669] text-white px-3 py-1.5 text-sm font-medium flex-1"
                      >
                        Подтвердить
                      </button>
                      <button 
                        onClick={() => handleReject(item.id)}
                        disabled={loading}
                        className="bg-[#EF4444] hover:bg-[#DC2626] text-white px-3 py-1.5 text-sm font-medium flex-1"
                      >
                        Отклонить
                      </button>
                      <button 
                        onClick={() => {
                          const sName = prompt('Введите часть названия услуги для поиска (например "МРТ"):');
                          if (sName && sName.trim().length > 0) {
                            handleApprove(item.id, null, parseFloat(item.new_price), parseFloat(item.new_price_nonresident), item.raw_name, sName.trim());
                          }
                        }}
                        className="bg-white border border-[#D1D5DB] hover:bg-[#F3F4F6] text-[#374151] px-3 py-1.5 text-sm font-medium flex-1"
                      >
                        Вручную
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
