import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { CheckCircle2, AlertTriangle, FileText, Activity, UploadCloud, Loader2 } from 'lucide-react';

export default function AdminDashboard() {
  const [anomalies, setAnomalies] = useState([]);
  const [stats, setStats] = useState({
    processed: 124,
    automationScore: 82,
    inQueue: 0,
    activeClinics: 42
  });
  
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [loading, setLoading] = useState(false);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchAnomalies();
  }, []);

  const fetchAnomalies = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/v1/admin/unmatched');
      setAnomalies(response.data);
      setStats(prev => ({ ...prev, inQueue: response.data.length }));
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
      const response = await axios.post('http://localhost:8000/api/v1/admin/upload-prices', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setUploadMessage(`Успешно: ${response.data.message}`);
      // В реальном приложении здесь можно запустить поллинг или WebSockets
      setTimeout(fetchAnomalies, 5000); 
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

  const handleApprove = async (id, serviceId, newPrice, newPriceNonresident, rawName) => {
    setLoading(true);
    try {
      // POST with the updated rawName and both prices
      const response = await axios.post(`http://localhost:8000/api/v1/admin/match/${id}?service_id=${serviceId}&price=${newPrice}&price_nonresident=${newPriceNonresident}&raw_name=${encodeURIComponent(rawName)}`);
      if (response.status === 200) {
        setAnomalies(prev => prev.filter(a => a.id !== id));
        setStats(prev => ({ ...prev, inQueue: prev.inQueue - 1 }));
      }
    } catch (error) {
      console.error("Ошибка при подтверждении:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#111827]">Панель оператора</h1>
        <p className="text-[#6B7280] mt-1">Аналитика, верификация парсинга и управление справочником</p>
      </div>

      {/* Upload Zone */}
      <div className="bg-white border border-[#E5E7EB] rounded-md p-8 flex flex-col items-center justify-center relative shadow-sm">
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
          className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-6 py-2.5 rounded-md font-medium transition-colors flex items-center gap-2"
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-[#E5E7EB] rounded-md p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <FileText size={20} />
            <h3 className="font-medium text-sm">Обработано прайсов</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827]">{stats.processed}</div>
        </div>
        
        <div className="bg-white border border-[#E5E7EB] rounded-md p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <CheckCircle2 size={20} />
            <h3 className="font-medium text-sm">Автонормализация</h3>
          </div>
          <div className="flex items-end gap-2">
            <div className="text-3xl font-bold text-[#059669]">{stats.automationScore}%</div>
            <span className="text-xs text-[#6B7280] mb-1">цель: 70%</span>
          </div>
          <div className="w-full bg-[#F3F4F6] h-1.5 rounded-full mt-3 overflow-hidden">
            <div className="bg-[#059669] h-full rounded-full" style={{ width: `${stats.automationScore}%` }}></div>
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-md p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <AlertTriangle size={20} />
            <h3 className="font-medium text-sm">В очереди (Аномалии)</h3>
          </div>
          <div className="text-3xl font-bold text-[#DC2626]">{stats.inQueue}</div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-md p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <Activity size={20} />
            <h3 className="font-medium text-sm">Активных клиник</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827]">{stats.activeClinics}</div>
        </div>
      </div>

      {/* Verification Queue (Split Screen) */}
      <div>
        <h2 className="text-lg font-bold text-[#111827] mb-4">Очередь верификации</h2>
        
        {anomalies.length === 0 ? (
          <div className="text-center py-12 bg-white border border-[#E5E7EB] rounded-md">
            <CheckCircle2 className="mx-auto h-12 w-12 text-[#D1D5DB] mb-3" />
            <h3 className="text-sm font-medium text-[#374151]">Очередь верификации пуста</h3>
            <p className="text-sm text-[#6B7280] mt-1">Загрузите ZIP-архив клиник для начала обработки.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {anomalies.map((item) => (
              <div 
                key={item.id} 
                className={`border rounded-md overflow-hidden shadow-sm ${item.status === 'anomaly' ? 'border-[#FBBF24] bg-[#FEFCE8]' : 'border-[#E5E7EB] bg-white'}`}
              >
                {item.status === 'anomaly' && (
                  <div className="bg-[#FEFCE8] border-b border-[#FBBF24] px-5 py-2 text-xs text-[#B45309] font-medium flex items-center gap-2">
                    <AlertTriangle size={14} />
                    {item.note || 'Требуется ручная проверка'}
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
                      className="font-medium text-[#111827] text-base mb-2 border border-[#D1D5DB] rounded px-2 py-1 w-full focus:ring-[#2563EB] focus:outline-none"
                    />
                    <div className="flex flex-col gap-2 text-sm mt-4">
                      {item.old_price && (
                        <div className="text-[#6B7280] mb-2">Старая цена (Рез): <span className="line-through">{item.old_price} ₸</span></div>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="w-24 text-[#6B7280]">Резидент:</span>
                        <div className="text-[#111827] font-semibold flex items-center">
                          <input 
                            type="number" 
                            value={item.new_price} 
                            onChange={e => handleRowChange(item.id, 'new_price', e.target.value)}
                            className="border border-[#D1D5DB] rounded px-2 py-1 w-24 text-sm mr-2 focus:ring-[#2563EB] focus:outline-none"
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
                            className="border border-[#D1D5DB] rounded px-2 py-1 w-24 text-sm mr-2 focus:ring-[#2563EB] focus:outline-none"
                          /> ₸
                        </div>
                      </div>

                      {item.diff && (
                        <div className={`font-bold text-xs ${item.status === 'anomaly' ? 'text-[#DC2626]' : 'text-[#6B7280]'}`}>
                          ({item.diff})
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Suggestion Block */}
                  <div className="flex-1 p-5 bg-white flex flex-col">
                    <div className="flex justify-between items-start mb-2">
                      <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Предложение ИИ</div>
                      {item.confidence && (
                        <div className="bg-[#ECFDF5] text-[#059669] px-2 py-0.5 rounded text-[11px] font-medium">
                          Уверенность: {item.confidence}%
                        </div>
                      )}
                    </div>
                    <div className="font-medium text-[#2563EB] text-base mb-4">{item.suggested_service_id ? `Услуга ID: ${item.suggested_service_id}` : 'Не сопоставлено'}</div>
                    
                    <div className="flex gap-2 mt-auto">
                      <button 
                        onClick={() => {
                          handleApprove(item.id, item.suggested_service_id, parseFloat(item.new_price), parseFloat(item.new_price_nonresident), item.raw_name);
                        }}
                        disabled={loading}
                        className="flex-1 bg-[#111827] hover:bg-[#374151] text-white px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                      >
                        Подтвердить
                      </button>
                      <button className="flex-1 bg-white border border-[#D1D5DB] hover:bg-[#F3F4F6] text-[#374151] px-3 py-1.5 rounded-md text-sm font-medium transition-colors">
                        Настроить вручную
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
