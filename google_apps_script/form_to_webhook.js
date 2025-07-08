/**
 * 멀티 시트 주차 자동화 시스템 - 완전한 중복 방지 버전
 * 
 * 구조:
 * - A매장 폼 → "A매장" 시트
 * - B매장 폼 → "B매장" 시트  
 * - 동탄점 폼 → "동탄점" 시트
 * 
 * 중복 방지: PropertiesService를 사용하여 실행간 데이터 지속성 보장
 */

// ===== 📝 설정 구간 (필요시 여기만 수정하세요) =====

// AWS API Gateway URL
const WEBHOOK_URL = 'https://cxs4uxpu3e.execute-api.ap-northeast-2.amazonaws.com/v1/webhook_test';

// 텔레그램 설정 (실패 알림용)
const TELEGRAM_BOT_TOKEN = '7694000458:AAFDa7szcGRjJJUy8cU_eJnU9MPgqsWnkmk';
const TELEGRAM_CHAT_ID = '6968094848';

// 중복 방지 시간 설정 (분 단위)
const DUPLICATE_WINDOW_MINUTES = 60; // 60분 = 1시간 (자유롭게 변경 가능: 30, 60, 120 등)

// 재시도 및 타임아웃 설정
const MAX_RETRIES = 3;           // 최대 재시도 횟수
const TIMEOUT_SECONDS = 30;      // 타임아웃 (초)
const RETRY_DELAY_MS = 1000;     // 재시도 간격 (밀리초)

// ===== 📝 설정 구간 끝 =====

// PropertiesService 키 (중복 방지 데이터 저장용)
const DUPLICATE_PREVENTION_KEY = 'PARKING_DUPLICATE_PREVENTION';

// 시트명 → 매장 정보 매핑
const SHEET_STORE_MAP = {
  'A매장': {
    store_id: 'A',
    name: 'A매장',
    vehicle_format: 'flexible',
    description: '주차쿠폰 신청',
    aliases: ['A매장', 'A점', 'A', 'store_a', 'STORE_A']
  },
  'B매장': {
    store_id: 'B', 
    name: 'B매장',
    vehicle_format: 'flexible',
    description: '주차쿠폰 신청',
    aliases: ['B매장', 'B점', 'B', 'store_b', 'STORE_B']
  },
  '동탄점': {
    store_id: 'A',
    name: '동탄점',
    vehicle_format: 'last4_preferred',
    description: '주차정산 신청',
    aliases: ['동탄점', '동탄', 'dontan', 'DONTAN', '동탄매장']
  }
};

/**
 * 중복 방지 데이터 로드 (PropertiesService에서)
 */
function loadDuplicatePreventionData() {
  try {
    const properties = PropertiesService.getScriptProperties();
    const dataString = properties.getProperty(DUPLICATE_PREVENTION_KEY);
    
    if (!dataString) {
      return {};
    }
    
    const data = JSON.parse(dataString);
    console.log(`📊 중복 방지 데이터 로드됨: ${Object.keys(data).length}개 항목`);
    return data;
  } catch (error) {
    console.error('⚠️ 중복 방지 데이터 로드 실패:', error);
    return {};
  }
}

/**
 * 중복 방지 데이터 저장 (PropertiesService에)
 */
function saveDuplicatePreventionData(data) {
  try {
    const properties = PropertiesService.getScriptProperties();
    properties.setProperty(DUPLICATE_PREVENTION_KEY, JSON.stringify(data));
    console.log(`💾 중복 방지 데이터 저장됨: ${Object.keys(data).length}개 항목`);
  } catch (error) {
    console.error('⚠️ 중복 방지 데이터 저장 실패:', error);
  }
}

/**
 * 오래된 중복 방지 데이터 정리
 */
function cleanupOldDuplicateData(data) {
  const now = Date.now();
  const cleanupTime = DUPLICATE_WINDOW_MINUTES * 2 * 60 * 1000; // 설정 시간의 2배 후 정리
  let cleanedCount = 0;
  
  for (const [key, requestData] of Object.entries(data)) {
    if (now - requestData.timestamp > cleanupTime) {
      delete data[key];
      cleanedCount++;
    }
  }
  
  if (cleanedCount > 0) {
    console.log(`🧹 오래된 중복 방지 데이터 ${cleanedCount}개 정리됨`);
  }
  
  return data;
}

/**
 * 고유 요청 키 생성 (시간창 기반)
 */
function generateRequestKey(sheetName, vehicleNumber, timestamp) {
  // 시간창 기반 (설정된 분 단위로 그룹핑)
  const timeWindow = Math.floor(timestamp / (DUPLICATE_WINDOW_MINUTES * 60 * 1000));
  return `${sheetName}-${vehicleNumber}-${timeWindow}`;
}

/**
 * 중복 요청 체크 및 등록
 */
function isDuplicateRequest(sheetName, vehicleNumber, storeInfo) {
  const now = Date.now();
  const requestKey = generateRequestKey(sheetName, vehicleNumber, now);
  
  // 기존 데이터 로드
  let duplicateData = loadDuplicatePreventionData();
  
  // 오래된 데이터 정리
  duplicateData = cleanupOldDuplicateData(duplicateData);
  
  // 중복 체크
  if (duplicateData[requestKey]) {
    const existingData = duplicateData[requestKey];
    console.log(`🔄 중복 요청 감지: ${requestKey}`);
    console.log(`📊 기존 요청: ${existingData.store} ${existingData.vehicle} (${new Date(existingData.timestamp).toLocaleString('ko-KR')})`);
    
    // 기존 요청이 여전히 유효한 시간창 내에 있는지 확인
    const timeDiff = now - existingData.timestamp;
    if (timeDiff < DUPLICATE_WINDOW_MINUTES * 60 * 1000) {
      return {
        isDuplicate: true,
        existingRequest: existingData,
        remainingTime: Math.ceil((DUPLICATE_WINDOW_MINUTES * 60 * 1000 - timeDiff) / 60000) // 분 단위
      };
    }
  }
  
  // 새로운 요청 등록
  duplicateData[requestKey] = {
    store: storeInfo.name,
    vehicle: vehicleNumber,
    timestamp: now,
    sheetName: sheetName
  };
  
  // 데이터 저장
  saveDuplicatePreventionData(duplicateData);
  
  console.log(`✅ 새로운 요청 등록: ${requestKey}`);
  return { isDuplicate: false };
}

/**
 * 시트명으로 매장 정보 찾기
 */
function getStoreInfoBySheetName(sheetName) {
  console.log('🔍 시트명으로 매장 정보 검색:', sheetName);
  
  // 정확한 매칭 먼저 시도
  if (SHEET_STORE_MAP[sheetName]) {
    console.log(`✅ 정확한 매칭 성공: ${sheetName}`);
    return SHEET_STORE_MAP[sheetName];
  }
  
  // aliases로 매칭 시도
  for (const [key, storeInfo] of Object.entries(SHEET_STORE_MAP)) {
    if (storeInfo.aliases.some(alias => 
      sheetName.toLowerCase().includes(alias.toLowerCase()) || 
      alias.toLowerCase().includes(sheetName.toLowerCase())
    )) {
      console.log(`✅ 별칭 매칭 성공: ${sheetName} → ${key}`);
      return storeInfo;
    }
  }
  
  console.log(`❌ 매장 정보를 찾을 수 없음: ${sheetName}`);
  return null;
}

/**
 * 차량번호 추출 함수
 */
function extractVehicleNumber(responses, storeInfo) {
  console.log('🚗 차량번호 추출 시작');
  
  // 차량번호 필드 우선순위
  const vehicleFieldPatterns = [
    /차량번호.*뒤.*4자리/i,
    /뒤.*4자리/i,
    /4자리/i,
    /차량번호/i,
    /차량/i,
    /vehicle/i,
    /car/i
  ];
  
  const responseKeys = Object.keys(responses);
  
  for (const pattern of vehicleFieldPatterns) {
    const matchingKey = responseKeys.find(key => pattern.test(key));
    if (matchingKey && responses[matchingKey] && responses[matchingKey][0]) {
      const value = responses[matchingKey][0].toString().trim();
      console.log(`🎯 패턴 매칭 성공 - 필드: "${matchingKey}", 값: "${value}"`);
      return value;
    }
  }
  
  const exactFieldNames = [
    '차량번호를 입력하세요',
    '차량번호',
    'vehicle_number',
    '차량번호 뒤 4자리를 입력해주세요.\n예) 5282',
    '차량번호 뒤 4자리를 입력해주세요. 예) 5282'
  ];
  
  for (const fieldName of exactFieldNames) {
    if (responses[fieldName] && responses[fieldName][0]) {
      const value = responses[fieldName][0].toString().trim();
      console.log(`🎯 정확한 필드명 매칭 - 필드: "${fieldName}", 값: "${value}"`);
      return value;
    }
  }
  
  console.log('❌ 차량번호를 찾을 수 없음');
  return null;
}

/**
 * 차량번호 유효성 검증 및 정규화
 */
function validateAndNormalizeVehicle(vehicleNumber, storeInfo) {
  if (!vehicleNumber) return { valid: false, error: '차량번호가 없습니다' };
  
  const cleaned = vehicleNumber.toString().trim();
  
  if (storeInfo.vehicle_format === 'last4_preferred') {
    if (/^\d{4}$/.test(cleaned)) {
      return { valid: true, normalized: cleaned, format: 'last4' };
    } else if (/^\d{2,3}[가-힣]\d{4}$/.test(cleaned)) {
      return { valid: true, normalized: cleaned, format: 'full' };
    } else {
      return { 
        valid: false, 
        error: `동탄점은 뒤 4자리 숫자(예: 5282) 또는 전체 차량번호(예: 12가3456)를 입력해주세요. 입력값: ${cleaned}` 
      };
    }
  } else {
    if (/^\d{4}$/.test(cleaned)) {
      return { valid: true, normalized: cleaned, format: 'last4' };
    } else if (/^\d{2,3}[가-힣]\d{4}$/.test(cleaned)) {
      return { valid: true, normalized: cleaned, format: 'full' };
    } else {
      return { 
        valid: false, 
        error: `차량번호는 전체(예: 12가3456) 또는 뒤 4자리(예: 3456) 형식으로 입력해주세요. 입력값: ${cleaned}` 
      };
    }
  }
}

/**
 * 재시도 로직이 포함된 Lambda 호출
 */
function sendToLambdaWithRetry(data, maxRetries = MAX_RETRIES) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`🚀 Lambda 호출 시도 ${attempt}/${maxRetries}`);
      
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-Attempt': attempt.toString()
        },
        payload: JSON.stringify(data),
        muteHttpExceptions: true
      };
      
      const startTime = Date.now();
      console.log(`🌐 API Gateway 호출: ${WEBHOOK_URL}`);
      
      const response = UrlFetchApp.fetch(WEBHOOK_URL, {
        ...options,
        deadline: TIMEOUT_SECONDS
      });
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      const statusCode = response.getResponseCode();
      const responseText = response.getContentText();
      
      console.log(`📊 Lambda 응답 - 시도: ${attempt}, 상태코드: ${statusCode}, 소요시간: ${duration}ms`);
      
      if (statusCode >= 200 && statusCode < 300) {
        let responseData = {};
        try {
          responseData = JSON.parse(responseText);
        } catch (e) {
          responseData = { raw: responseText };
        }
        
        console.log(`✅ Lambda 호출 성공 (시도 ${attempt}/${maxRetries})`);
        return {
          success: true,
          statusCode: statusCode,
          data: responseData,
          attempts: attempt,
          duration: duration
        };
      } else if (statusCode >= 500 && attempt < maxRetries) {
        // 5xx 에러는 재시도
        console.log(`⚠️ 서버 오류 (${statusCode}), ${RETRY_DELAY_MS}ms 후 재시도...`);
        Utilities.sleep(RETRY_DELAY_MS);
        continue;
      } else {
        // 4xx 에러는 재시도하지 않음
        return {
          success: false,
          statusCode: statusCode,
          error: `HTTP ${statusCode}: ${responseText}`,
          attempts: attempt,
          duration: duration
        };
      }
      
    } catch (error) {
      console.error(`🔥 Lambda 호출 오류 (시도 ${attempt}/${maxRetries}):`, error);
      
      if (attempt < maxRetries) {
        console.log(`⚠️ ${RETRY_DELAY_MS}ms 후 재시도...`);
        Utilities.sleep(RETRY_DELAY_MS);
        continue;
      } else {
        return {
          success: false,
          error: error.message,
          attempts: attempt
        };
      }
    }
  }
  
  return {
    success: false,
    error: `모든 재시도 실패 (${maxRetries}회 시도)`,
    attempts: maxRetries
  };
}

/**
 * 폼 제출 이벤트 핸들러 (메인 함수)
 */
function onFormSubmit(e) {
  const startTime = Date.now();
  
  try {
    console.log('📝 === 폼 제출 감지 ===');
    
    const responses = e.namedValues;
    const range = e.range;
    const sheet = range.getSheet();
    const sheetName = sheet.getName();
    const rowNumber = range.getRow();
    const timestamp = new Date();
    
    console.log(`📊 응답 시트: "${sheetName}", 행: ${rowNumber}`);
    console.log(`⏰ 처리 시작 시간: ${timestamp.toLocaleString('ko-KR')}`);
    
    // 1. 시트명으로 매장 정보 찾기
    const storeInfo = getStoreInfoBySheetName(sheetName);
    if (!storeInfo) {
      throw new Error(`지원하지 않는 시트입니다: "${sheetName}". 지원되는 시트: ${Object.keys(SHEET_STORE_MAP).join(', ')}`);
    }
    
    // 2. 차량번호 추출
    const vehicleNumber = extractVehicleNumber(responses, storeInfo);
    if (!vehicleNumber) {
      throw new Error('차량번호를 찾을 수 없습니다. 폼에 차량번호 필드가 있는지 확인해주세요.');
    }
    
    // 3. 차량번호 검증
    const validation = validateAndNormalizeVehicle(vehicleNumber, storeInfo);
    if (!validation.valid) {
      throw new Error(validation.error);
    }
    
    console.log(`🚗 차량번호 검증 완료: ${validation.normalized} (${validation.format} 형식)`);
    
    // 4. 중복 요청 체크 (PropertiesService 기반)
    const duplicateCheck = isDuplicateRequest(sheetName, validation.normalized, storeInfo);
    
    if (duplicateCheck.isDuplicate) {
      const warningMessage = `⚠️ 중복 요청 감지 - 무시됨

🏪 매장: ${storeInfo.name}
🚗 차량번호: ${validation.normalized}
📋 시트: ${sheetName}
📍 행번호: ${rowNumber}
⏰ 현재시간: ${timestamp.toLocaleString('ko-KR')}
📅 기존요청: ${new Date(duplicateCheck.existingRequest.timestamp).toLocaleString('ko-KR')}
🕐 중복방지시간: ${DUPLICATE_WINDOW_MINUTES}분
⏳ 남은시간: ${duplicateCheck.remainingTime}분

동일한 요청이 ${DUPLICATE_WINDOW_MINUTES}분 내에 이미 처리되었습니다.`;

      console.log('⚠️ 중복 요청으로 인한 종료');
      sendTelegramMessage(warningMessage);
      markProcessingStatus(sheet, rowNumber, 'DUPLICATE', `⚠️ 중복요청 (${duplicateCheck.remainingTime}분 남음)`);
      return;
    }
    
    // 5. 시트에 처리 시작 상태 기록
    markProcessingStatus(sheet, rowNumber, 'PROCESSING', '⏳ 처리중...');
    
    // 6. Lambda 전송 데이터 구성
    const payload = {
      store_id: storeInfo.store_id,
      vehicle_number: validation.normalized
    };
    
    console.log('🚀 AWS Lambda로 전송할 데이터:', payload);
    
    // 7. Lambda 호출 (재시도 로직 포함)
    const response = sendToLambdaWithRetry(payload);
    
    if (response.success) {
      console.log(`✅ Lambda 호출 성공 (${response.attempts}회 시도, ${response.duration}ms 소요)`);
      markProcessingStatus(sheet, rowNumber, 'SUCCESS', '✅ 처리완료');
    } else {
      throw new Error(`Lambda 호출 실패: ${response.error} (${response.attempts || 0}회 시도)`);
    }
    
  } catch (error) {
    console.error('❌ 폼 처리 오류:', error);
    
    const totalTime = Date.now() - startTime;
    
    // 오류 정보 수집
    const errorInfo = {
      message: error.message,
      timestamp: new Date().toLocaleString('ko-KR'),
      sheetName: e.range ? e.range.getSheet().getName() : '알 수 없음',
      rowNumber: e.range ? e.range.getRow() : '알 수 없음',
      processingTime: totalTime,
      duplicateWindow: DUPLICATE_WINDOW_MINUTES
    };
    
    // 텔레그램 오류 알림 (실패시에만 전송)
    const errorMessage = `❌ 주차 자동화 처리 오류

📋 시트: ${errorInfo.sheetName}
📍 행번호: ${errorInfo.rowNumber}
⚠️ 오류내용: ${errorInfo.message}
⏰ 발생시간: ${errorInfo.timestamp}
⚡ 처리시간: ${errorInfo.processingTime}ms
🕐 중복방지시간: ${errorInfo.duplicateWindow}분

시스템 오류이거나 네트워크 문제일 수 있습니다.`;
    
    sendTelegramMessage(errorMessage);
    
    // 시트에 오류 상태 기록
    if (e.range) {
      markProcessingStatus(e.range.getSheet(), e.range.getRow(), 'ERROR', `❌ ${error.message.substring(0, 100)}`);
    }
    
    throw error;
  }
}

/**
 * 시트에 처리 상태 기록
 */
/**
 * 시트의 D열(4번째 열)에 최종 처리 상태만 기록
 */
function markProcessingStatus(sheet, rowNumber, status, message) {
  try {
    const statusColumn = 4; // D열은 열 번호 4번

    // 상태 메시지 기록
    sheet.getRange(rowNumber, statusColumn).setValue(message);

    console.log(`📝 처리상태 기록: 행 ${rowNumber}, D열, 상태: ${status}`);

  } catch (error) {
    console.error('⚠️ 처리상태 기록 실패:', error);
  }
}

/**
 * 텔레그램 알림 전송 (실패시에만)
 */
function sendTelegramMessage(message) {
  try {
    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
      console.log('📱 텔레그램 설정이 없어 알림을 보내지 않습니다');
      return false;
    }
    
    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
    const payload = {
      chat_id: TELEGRAM_CHAT_ID,
      text: message,
      parse_mode: 'HTML'
    };
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      payload: JSON.stringify(payload),
      deadline: 10
    };
    
    const response = UrlFetchApp.fetch(url, options);
    console.log(`📱 텔레그램 알림 전송 완료 - 상태: ${response.getResponseCode()}`);
    return true;
    
  } catch (error) {
    console.error('📱 텔레그램 알림 전송 실패:', error);
    return false;
  }
}

/**
 * 중복 방지 데이터 수동 정리 (관리용 함수)
 */
function clearAllDuplicateData() {
  try {
    const properties = PropertiesService.getScriptProperties();
    properties.deleteProperty(DUPLICATE_PREVENTION_KEY);
    console.log('🧹 모든 중복 방지 데이터가 정리되었습니다');
  } catch (error) {
    console.error('❌ 중복 방지 데이터 정리 실패:', error);
  }
}