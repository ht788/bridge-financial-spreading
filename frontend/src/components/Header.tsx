import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, Zap, FlaskConical, Bell, BellOff, Edit3 } from 'lucide-react';
import { 
  isNotificationSupported, 
  getNotificationPermission, 
  requestNotificationPermission 
} from '../utils/notifications';

interface HeaderProps {
  onNavigateToTesting?: () => void;
  onNavigateToHome?: () => void;
  onNavigateToAnswerKeys?: () => void;
  currentPage?: 'home' | 'testing' | 'answer-keys';
}

export const Header: React.FC<HeaderProps> = ({ 
  onNavigateToTesting, 
  onNavigateToHome,
  onNavigateToAnswerKeys,
  currentPage = 'home' 
}) => {
  const [notificationPermission, setNotificationPermission] = useState(getNotificationPermission());
  const [isRequestingPermission, setIsRequestingPermission] = useState(false);

  useEffect(() => {
    // Update permission state if it changes
    const checkPermission = () => {
      setNotificationPermission(getNotificationPermission());
    };
    
    // Check on visibility change (in case user changed it in browser settings)
    document.addEventListener('visibilitychange', checkPermission);
    
    return () => {
      document.removeEventListener('visibilitychange', checkPermission);
    };
  }, []);

  const handleRequestNotifications = async () => {
    if (!isNotificationSupported()) {
      alert('Notifications are not supported in your browser.');
      return;
    }

    if (notificationPermission === 'denied') {
      alert('Notifications are blocked. Please enable them in your browser settings.');
      return;
    }

    setIsRequestingPermission(true);
    try {
      const permission = await requestNotificationPermission();
      setNotificationPermission(permission);
      
      if (permission === 'granted') {
        // Show a test notification
        new Notification('✅ Notifications Enabled', {
          body: 'You\'ll receive notifications when processing completes.',
          icon: '/bridge-icon.png',
        });
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error);
    } finally {
      setIsRequestingPermission(false);
    }
  };

  const getNotificationButtonConfig = () => {
    if (!isNotificationSupported()) {
      return null; // Hide button if not supported
    }

    switch (notificationPermission) {
      case 'granted':
        return {
          icon: Bell,
          label: 'Notifications On',
          color: 'text-green-600 hover:text-green-700 hover:bg-green-50',
          title: 'Notifications are enabled',
        };
      case 'denied':
        return {
          icon: BellOff,
          label: 'Notifications Blocked',
          color: 'text-red-600 hover:text-red-700 hover:bg-red-50',
          title: 'Enable notifications in browser settings',
        };
      default:
        return {
          icon: Bell,
          label: 'Enable Notifications',
          color: 'text-gray-600 hover:text-gray-900 hover:bg-gray-100',
          title: 'Click to enable notifications',
        };
    }
  };

  const notificationButton = getNotificationButtonConfig();

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button 
              onClick={onNavigateToHome}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity"
            >
              <div className="bg-gradient-to-br from-emerald-500 to-teal-600 p-2.5 rounded-xl shadow-lg shadow-emerald-500/20">
                <FileSpreadsheet className="w-6 h-6 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  Bridge Financial Spreader
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold rounded-full">
                    <Zap className="w-3 h-3" />
                    AI
                  </span>
                </h1>
                <p className="text-sm text-gray-500">
                  Vision-First Financial Statement Analysis
                </p>
              </div>
            </button>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-2">
            {/* Notification Toggle */}
            {notificationButton && (
              <button
                onClick={handleRequestNotifications}
                disabled={isRequestingPermission || notificationPermission === 'granted'}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl font-medium transition-all ${notificationButton.color} ${
                  (isRequestingPermission || notificationPermission === 'granted') ? 'opacity-60 cursor-default' : ''
                }`}
                title={notificationButton.title}
              >
                <notificationButton.icon className="w-4 h-4" />
                <span className="hidden sm:inline text-sm">
                  {notificationButton.label}
                </span>
              </button>
            )}
            
            <button
              onClick={onNavigateToTesting}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
                currentPage === 'testing'
                  ? 'bg-violet-100 text-violet-700 ring-2 ring-violet-500/20'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <FlaskConical className="w-4 h-4" />
              Testing Lab
            </button>

            <button
              onClick={onNavigateToAnswerKeys}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
                currentPage === 'answer-keys'
                  ? 'bg-amber-100 text-amber-700 ring-2 ring-amber-500/20'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Edit3 className="w-4 h-4" />
              Answer Keys
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
