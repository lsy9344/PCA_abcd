/**
 * 멀티 시트 주차 자동화 시스템 - 최종 완성본
 * - 기능: 중복 방지, 다중 등록 감지(수정됨), 백엔드 알림 연동
 */

// ===== 📝 설정 구간 (필요시 여기만 수정하세요) =====

// AWS API Gateway URL
const WEBHOOK_URL = 'https://ygfrdci383.execute-api.ap-northeast-2.amazonaws.com/parkingauto_250707';

// 텔레그램 설정 (알림용)
const TELEGRAM_BOT_TOKEN = '7694000458:AAFDa7szcGRjJJUy8cU_eJnU9MPgqsWnkmk';
const TELEGRAM_CHAT_ID = '6968094848';

// 중복 방지 시간 설정 (분 단위)
const DUPLICATE_WINDOW_MINUTES = 60;

// 다중 등록 감지 시간 설정 (분 단위)
const MULTI_SUBMISSION_WINDOW_MINUTES = 40;

// 재시도 및 타임아웃 설정
const MAX_RETRIES = 3;
const TIMEOUT_SECONDS = 30;
const RETRY_DELAY_MS = 1000;

// ===== 📝 설정 구간 끝 =====

// PropertiesService 키
const DUPLICATE_PREVENTION_KEY = 'PARKING_DUPLICATE_PREVENTION';
const MULTI_SUBMISSION_KEY = 'PARKING_MULTI_SUBMISSION_TIMESTAMPS';


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
  'C매장': {
    store_id: 'C',
    name: 'C매장',
    vehicle_format: 'flexible',
    description: '주차쿠폰 신청',
    aliases: ['C매장', 'C점', 'C', 'store_c', 'STORE_C']
  },
  'D매장': {
    store_id: 'D',
    name: 'D매장',
    vehicle_format: 'flexible',
    description: '주차쿠폰 신청',
    aliases: ['D매장', 'D점', 'D', 'store_d', 'STORE_D']
  },
  'E매장': {
    store_id: 'E',
    name: 'E매장',
    vehicle_format: 'flexible',
    description: '주차쿠폰 신청',
    aliases: ['E매장', 'E점', 'E', 'store_e', 'STORE_E']
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
 * [수정됨] 40분 내 다중 제출 감지 및 알림
 */
function handleMultiSubmissionCheck(sheetName, storeInfo) {
  try {
    const now = Date.now();
    const properties = PropertiesService.getScriptProperties();
    const timestampsString = properties.getProperty(MULTI_SUBMISSION_KEY);
    const timestamps = timestampsString ? JSON.parse(timestampsString) : {};
    const lastSubmissionTime = timestamps[sheetName];

    if (lastSubmissionTime) {
      const timeDiffMinutes = (now - lastSubmissionTime) / (60 * 1000);

      if (timeDiffMinutes < MULTI_SUBMISSION_WINDOW_MINUTES) {
        // 40분 내의 추가 제출이므로 알림만 보내고 시간은 갱신하지 않음
        console.log(`🚨 다중 등록 감지 (${storeInfo.name}, ${Math.floor(timeDiffMinutes)}분 전)`);
        const alertMessage = `🚨 차량 여러대 등록 감지\n\n🏪 매장: ${storeInfo.name}\n📋 시트: ${sheetName}\n⏰ 현재시간: ${new Date(now).toLocaleString('ko-KR')}\n⏱️ 이전 제출 후: ${Math.floor(timeDiffMinutes)}분 경과\n\n${MULTI_SUBMISSION_WINDOW_MINUTES}분 내에 여러 차량이 등록되었습니다.\nCCTV로 인원수를 확인하세요.`;
        sendTelegramMessage(alertMessage);
      } else {
        // 40분이 지난 후의 제출이므로, 이때만 마지막 제출 시간을 갱신
        timestamps[sheetName] = now;
        properties.setProperty(MULTI_SUBMISSION_KEY, JSON.stringify(timestamps));
      }
    } else {
      // 최초 제출이므로 마지막 제출 시간을 갱신
      timestamps[sheetName] = now;
      properties.setProperty(MULTI_SUBMISSION_KEY, JSON.stringify(timestamps));
    }
  } catch (error) {
    console.error('⚠️ 다중 제출 감지 기능 오류:', error);
  }
}


/**
 * 중복 방지 데이터 로드 (PropertiesService에서)
 */
function loadDuplicatePreventionData() {
  try {
    const properties = PropertiesService.getScriptProperties();
    const dataString = properties.getProperty(DUPLICATE_PREVENTION_KEY);
    if (!dataString) return {};
    return JSON.parse(dataString);
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
  } catch (error) {
    console.error('⚠️ 중복 방지 데이터 저장 실패:', error);
  }
}

/**
 * 오래된 중복 방지 데이터 정리
 */
function cleanupOldDuplicateData(data) {
  const now = Date.now();
  const cleanupTime = DUPLICATE_WINDOW_MINUTES * 2 * 60 * 1000;
  let cleanedCount = 0;
  for (const key in data) {
    if (now - data[key].timestamp > cleanupTime) {
      delete data[key];
      cleanedCount++;
    }
  }
  if (cleanedCount > 0) console.log(`🧹 오래된 중복 방지 데이터 ${cleanedCount}개 정리됨`);
  return data;
}

/**
 * 고유 요청 키 생성 (시간창 기반)
 */
function generateRequestKey(sheetName, vehicleNumber, timestamp) {
  const timeWindow = Math.floor(timestamp / (DUPLICATE_WINDOW_MINUTES * 60 * 1000));
  return `${sheetName}-${vehicleNumber}-${timeWindow}`;
}

/**
 * 중복 요청 체크 및 등록
 */
function isDuplicateRequest(sheetName, vehicleNumber) {
  const now = Date.now();
  const requestKey = generateRequestKey(sheetName, vehicleNumber, now);
  let duplicateData = loadDuplicatePreventionData();
  duplicateData = cleanupOldDuplicateData(duplicateData);

  if (duplicateData[requestKey]) {
    const existingData = duplicateData[requestKey];
    const timeDiff = now - existingData.timestamp;
    if (timeDiff < DUPLICATE_WINDOW_MINUTES * 60 * 1000) {
      return {
        isDuplicate: true,
        remainingTime: Math.ceil((DUPLICATE_WINDOW_MINUTES * 60 * 1000 - timeDiff) / 60000)
      };
    }
  }
  duplicateData[requestKey] = { vehicle: vehicleNumber, timestamp: now };
  saveDuplicatePreventionData(duplicateData);
  return { isDuplicate: false };
}

/**
 * 시트명으로 매장 정보 찾기
 */
function getStoreInfoBySheetName(sheetName) {
  if (SHEET_STORE_MAP[sheetName]) return SHEET_STORE_MAP[sheetName];
  for (const key in SHEET_STORE_MAP) {
    const storeInfo = SHEET_STORE_MAP[key];
    if (storeInfo.aliases.some(alias => sheetName.toLowerCase().includes(alias.toLowerCase()))) {
      return storeInfo;
    }
  }
  return null;
}

/**
 * 차량번호 추출 함수
 */
function extractVehicleNumber(responses) {
  const patterns = [/차량번호.*뒤.*4자리/i, /뒤.*4자리/i, /4자리/i, /차량번호/i, /차량/i, /vehicle/i, /car/i];
  const exactFieldNames = ['차량번호를 입력하세요', '차량번호', 'vehicle_number', '차량번호 뒤 4자리를 입력해주세요.\n예) 5282', '차량번호 뒤 4자리를 입력해주세요. 예) 5282'];
  const responseKeys = Object.keys(responses);

  for (const pattern of patterns) {
    const key = responseKeys.find(k => pattern.test(k));
    if (key && responses[key][0]) return responses[key][0].toString().trim();
  }
  for (const fieldName of exactFieldNames) {
    if (responses[fieldName] && responses[fieldName][0]) return responses[fieldName][0].toString().trim();
  }
  return null;
}

/**
 * 차량번호 유효성 검증 및 정규화
 */
function validateAndNormalizeVehicle(vehicleNumber, storeInfo) {
  if (!vehicleNumber) return { valid: false, error: '차량번호가 없습니다' };
  const cleaned = vehicleNumber.toString().trim();
  if (/^\d{4}$/.test(cleaned) || /^\d{2,3}[가-힣]\d{4}$/.test(cleaned)) {
    return { valid: true, normalized: cleaned };
  }
  let errorMsg = `잘못된 차량번호 형식입니다. 입력값: ${cleaned}`;
  if (storeInfo.vehicle_format === 'last4_preferred') {
    errorMsg = `동탄점은 뒤 4자리 숫자 또는 전체 차량번호를 입력해주세요. 입력값: ${cleaned}`;
  }
  return { valid: false, error: errorMsg };
}

/**
 * 재시도 로직이 포함된 Lambda 호출
 */
function sendToLambdaWithRetry(payload) {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
        deadline: TIMEOUT_SECONDS
      };
      const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
      const statusCode = response.getResponseCode();
      if (statusCode >= 200 && statusCode < 300) return { success: true };
      if (statusCode >= 500 && attempt < MAX_RETRIES) {
        Utilities.sleep(RETRY_DELAY_MS);
        continue;
      }
      return { success: false, error: `HTTP ${statusCode}: ${response.getContentText()}` };
    } catch (error) {
      if (attempt < MAX_RETRIES) {
        Utilities.sleep(RETRY_DELAY_MS);
        continue;
      }
      return { success: false, error: error.message };
    }
  }
  return { success: false, error: `모든 재시도 실패 (${MAX_RETRIES}회)` };
}

/**
 * 폼 제출 이벤트 핸들러 (메인 함수)
 */
function onFormSubmit(e) {
  try {
    const { namedValues: responses, range } = e;
    const sheet = range.getSheet();
    const sheetName = sheet.getName();
    const rowNumber = range.getRow();

    const storeInfo = getStoreInfoBySheetName(sheetName);
    if (!storeInfo) throw new Error(`지원하지 않는 시트: "${sheetName}"`);

    const vehicleNumberRaw = extractVehicleNumber(responses);
    const validation = validateAndNormalizeVehicle(vehicleNumberRaw, storeInfo);
    if (!validation.valid) throw new Error(validation.error);
    const { normalized: vehicleNumber } = validation;

    handleMultiSubmissionCheck(sheetName, storeInfo);

    const duplicateCheck = isDuplicateRequest(sheetName, vehicleNumber);
    if (duplicateCheck.isDuplicate) {
      const { remainingTime } = duplicateCheck;
      markProcessingStatus(sheet, rowNumber, `⚠️ 중복요청 (${remainingTime}분)`);
      const warningMessage = `⚠️ 1차량 중복 요청 감지\n\n🏪 매장: ${storeInfo.name}\n🚗 차량번호: ${vehicleNumber}\n⏳ 남은시간: ${remainingTime}분\n\n람다가 동작하지 않습니다.`;
      sendTelegramMessage(warningMessage);
      return;
    }

    markProcessingStatus(sheet, rowNumber, '⏳ 처리중...');

    const payload = { store_id: storeInfo.store_id, vehicle_number: vehicleNumber };
    const response = sendToLambdaWithRetry(payload);

    if (response.success) {
      markProcessingStatus(sheet, rowNumber, '✅ 처리완료');
    } else {
      throw new Error(response.error);
    }
  } catch (error) {
    console.error('❌ 폼 처리 오류:', error);
    
    // 백엔드에서 더 상세한 알림을 보내주므로, Apps Script의 중복 알림은 비활성화합니다.
    if (e.range) {
      markProcessingStatus(e.range.getSheet(), e.range.getRow(), `❌ 오류: ${error.message.substring(0, 100)}`);
    }
    throw error;
  }
}

/**
 * 시트의 D열(4번째 열)에 최종 처리 상태만 기록
 */
function markProcessingStatus(sheet, rowNumber, message) {
  try {
    sheet.getRange(rowNumber, 4).setValue(message);
  } catch (error) {
    console.error('⚠️ 처리상태 기록 실패:', error);
  }
}

/**
 * 텔레그램 알림 전송
 */
function sendTelegramMessage(message) {
  try {
    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) return;
    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
    const payload = { chat_id: TELEGRAM_CHAT_ID, text: message, parse_mode: 'HTML' };
    const options = { method: 'POST', headers: { 'Content-Type': 'application/json' }, payload: JSON.stringify(payload), deadline: 10 };
    UrlFetchApp.fetch(url, options);
  } catch (error) {
    console.error('📱 텔레그램 알림 전송 실패:', error);
  }
}

/**
 * 중복 방지 데이터 수동 정리 (관리용 함수)
 */
function clearAllDuplicateData() {
  try {
    const properties = PropertiesService.getScriptProperties();
    properties.deleteProperty(DUPLICATE_PREVENTION_KEY);
    properties.deleteProperty(MULTI_SUBMISSION_KEY);
    console.log('🧹 모든 중복 방지 및 다중 등록 감지 데이터가 정리되었습니다');
  } catch (error) {
    console.error('❌ 데이터 정리 실패:', error);
  }
}