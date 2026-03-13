#!/usr/bin/env node

const https = require('https');
const { generateRequestUrl, ROUTES } = require('./Hkey.js');
const localAuth = require('./local_auth.js');

const DEFAULT_TEST_PARAMS = {
    data_report: { type: '104' },
    search_found: { force_refresh: 'false' },
    general_search_v1: { q: '模拟' },
    feeds: { pull: '0', offset: '0', dw: '844' },
    news_list: { offset: '0', limit: '5' },
    recommend_user: { offset: '0', limit: '5' },
    hot_topics: { offset: '0', limit: '5' },
    game_list: { offset: '0', limit: '5' },
    notifications: { notice_type: '0' },
    related_recommend_web: { link_id: '175495445', h_src: 'FxDNnklDNXqYrPXG7' }
};

function getRuntimeConfig() {
    const referer = localAuth.referer || process.env.XHH_REFERER || 'https://www.xiaoheihe.cn/';
    const origin = localAuth.origin || process.env.XHH_ORIGIN || 'https://www.xiaoheihe.cn';
    const userAgent = localAuth.userAgent || process.env.XHH_USER_AGENT || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36';
    const cookie = localAuth.cookie || process.env.XHH_COOKIE || '';

    const baseOverrides = {
        heybox_id: localAuth.heyboxId || process.env.XHH_HEYBOX_ID || '',
        x_os_type: localAuth.xOsType || process.env.XHH_X_OS_TYPE || 'Windows',
        device_info: localAuth.deviceInfo || process.env.XHH_DEVICE_INFO || 'Chrome',
        device_id: localAuth.deviceId || process.env.XHH_DEVICE_ID || '2c2fef8385ccef915e3b3caf94e3aa06'
    };

    const headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': origin,
        'referer': referer,
        'user-agent': userAgent
    };

    if (cookie) {
        headers.cookie = cookie;
    }

    return { headers, baseOverrides, cookie };
}

function doGet(url, headers) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, {
            headers
        }, (res) => {
            let body = '';
            res.setEncoding('utf8');

            res.on('data', (chunk) => {
                body += chunk;
            });

            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    statusMessage: res.statusMessage,
                    headers: res.headers,
                    body
                });
            });
        });

        req.on('error', reject);
        req.end();
    });
}

function hasRequiredParams(routeName) {
    const route = ROUTES[routeName];
    if (!route) {
        return false;
    }

    return Object.values(route.params).some((value) => value === '');
}

function getMissingParamNames(routeName) {
    const route = ROUTES[routeName];
    if (!route) {
        return [];
    }

    return Object.entries(route.params)
        .filter(([, value]) => value === '')
        .map(([key]) => key);
}

function classifyJson(json, statusCode) {
    const status = typeof json?.status === 'string' ? json.status.toLowerCase() : '';
    const code = json?.code;
    const msg = json?.msg || json?.message || '';

    if (statusCode >= 200 && statusCode < 300) {
        if (status === 'ok' || code === 0 || code === '0') {
            return { level: 'success', reason: msg || status || 'ok' };
        }

        if (typeof msg === 'string') {
            const lower = msg.toLowerCase();
            if (lower.includes('login') || msg.includes('登录')) {
                return { level: 'auth', reason: msg };
            }
            if (msg.includes('参数') || lower.includes('param')) {
                return { level: 'param', reason: msg };
            }
        }

        return { level: 'unknown', reason: msg || status || `HTTP ${statusCode}` };
    }

    return { level: 'error', reason: msg || `HTTP ${statusCode}` };
}

function summarizeBody(body) {
    try {
        const json = JSON.parse(body);
        const classified = classifyJson(json, 200);
        const keys = Object.keys(json).slice(0, 8).join(', ');
        return {
            parsed: true,
            json,
            summary: classified.reason || keys || 'json response'
        };
    } catch {
        return {
            parsed: false,
            json: null,
            summary: body.replace(/\s+/g, ' ').slice(0, 140) || '(empty response)'
        };
    }
}

async function testRoute(routeName, runtimeConfig) {
    const route = ROUTES[routeName];
    const params = DEFAULT_TEST_PARAMS[routeName] || {};
    const missingParams = Object.entries(route.params)
        .filter(([key, value]) => value === '' && !(key in params))
        .map(([key]) => key);

    if (missingParams.length > 0) {
        return {
            routeName,
            path: route.path,
            status: 'skipped',
            reason: `缺少必填参数: ${missingParams.join(', ')}`,
            httpStatus: null
        };
    }

    const requestInfo = generateRequestUrl(routeName, params, runtimeConfig.baseOverrides);

    try {
        const response = await doGet(requestInfo.url, runtimeConfig.headers);
        const parsed = summarizeBody(response.body);

        let status = 'unknown';
        let reason = parsed.summary;

        if (response.statusCode >= 200 && response.statusCode < 300) {
            if (parsed.parsed) {
                const classified = classifyJson(parsed.json, response.statusCode);
                status = classified.level;
                reason = classified.reason || parsed.summary;
            } else {
                status = 'success';
            }
        } else {
            status = 'error';
            reason = parsed.summary;
        }

        return {
            routeName,
            path: route.path,
            status,
            reason,
            httpStatus: response.statusCode,
            url: requestInfo.url
        };
    } catch (error) {
        return {
            routeName,
            path: route.path,
            status: 'error',
            reason: error.message,
            httpStatus: null,
            url: requestInfo.url
        };
    }
}

function printResultLine(result) {
    const http = result.httpStatus === null ? '-' : String(result.httpStatus);
    console.log(`[${result.status.padEnd(7, ' ')}] ${result.routeName.padEnd(16, ' ')} HTTP ${http.padEnd(3, ' ')} ${result.reason}`);
}

function printSummary(results) {
    const counts = results.reduce((acc, item) => {
        acc[item.status] = (acc[item.status] || 0) + 1;
        return acc;
    }, {});

    console.log('\n' + '='.repeat(60));
    console.log('汇总');
    console.log('='.repeat(60));
    console.log(`success: ${counts.success || 0}`);
    console.log(`auth:    ${counts.auth || 0}`);
    console.log(`param:   ${counts.param || 0}`);
    console.log(`unknown: ${counts.unknown || 0}`);
    console.log(`skipped: ${counts.skipped || 0}`);
    console.log(`error:   ${counts.error || 0}`);
}

async function main() {
    const routeNames = Object.keys(ROUTES);
    const runtimeConfig = getRuntimeConfig();

    console.log('='.repeat(60));
    console.log('小黑盒 API 批量测试');
    console.log('='.repeat(60));
    console.log(`route count: ${routeNames.length}`);
    console.log(`cookie: ${runtimeConfig.cookie ? 'provided' : 'not provided'}`);
    console.log('');

    const results = [];
    for (const routeName of routeNames) {
        const result = await testRoute(routeName, runtimeConfig);
        results.push(result);
        printResultLine(result);
    }

    printSummary(results);

    console.log('\n需要补参数后再测的路由:');
    results
        .filter((item) => item.status === 'skipped')
        .forEach((item) => console.log(`- ${item.routeName}: ${item.reason}`));

    console.log('\n疑似需要登录或受限的路由:');
    results
        .filter((item) => item.status === 'auth')
        .forEach((item) => console.log(`- ${item.routeName}: ${item.reason}`));
}

main();
