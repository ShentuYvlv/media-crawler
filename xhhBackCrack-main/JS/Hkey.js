const crypto = require('crypto');

// --- 基础混淆函数 ---
function Vm(e) {
    if (e & 128) {
        return (255 & ((e << 1) ^ 27));
    } else {
        return e << 1;
    }
}

function qm(e) {
    return Vm(e) ^ e;
}

function dollar_m(e) {
    return qm(Vm(e));
}

function Ym(e) {
    return dollar_m(qm(Vm(e)));
}

function Gm(e) {
    return Ym(e) ^ dollar_m(e) ^ qm(e);
}

function Km_full(e_arr) {
    // 处理数组变换
    const e = [...e_arr]; // 复制数组
    const t = [0, 0, 0, 0];
    t[0] = Gm(e[0]) ^ Ym(e[1]) ^ dollar_m(e[2]) ^ qm(e[3]);
    t[1] = qm(e[0]) ^ Gm(e[1]) ^ Ym(e[2]) ^ dollar_m(e[3]);
    t[2] = dollar_m(e[0]) ^ qm(e[1]) ^ Gm(e[2]) ^ Ym(e[3]);
    t[3] = Ym(e[0]) ^ dollar_m(e[1]) ^ qm(e[2]) ^ Gm(e[3]);

    // 更新前4位
    e[0] = t[0];
    e[1] = t[1];
    e[2] = t[2];
    e[3] = t[3];
    return e;
}

// --- 映射函数 ---
function av(e, t, n) {
    /**
     * e: 输入字符串
     * t: 字符集
     * n: 切片长度 (负数表示切掉末尾)
     */
    let i;
    if (n < 0) {
        i = t.slice(0, n);
    } else {
        i = t.slice(0, n);
    }

    let r = "";
    for (let char of e) {
        const idx = char.charCodeAt(0) % i.length;
        r += i[idx];
    }
    return r;
}

function sv(e, t) {
    /**
     * e: 输入字符串
     * t: 字符集
     */
    let n_str = "";
    for (let char of e) {
        const idx = char.charCodeAt(0) % t.length;
        n_str += t[idx];
    }
    return n_str;
}

function get_hkey(url_path, timestamp, nonce) {
    // 1. 字符集
    const charset = "AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89";

    // 2. 路径标准化
    const parts = url_path.split('/').filter(p => p);
    const normalized_path = "/" + parts.join("/") + "/";

    // 3. 生成三个分量
    // 分量1: 处理时间戳 (使用字符集的前34位，即切掉后2位)
    const comp1 = av(String(timestamp), charset, -2);

    // 分量2: 处理路径 (使用完整字符集)
    const comp2 = sv(normalized_path, charset);

    // 分量3: 处理Nonce (使用完整字符集)
    const comp3 = sv(nonce, charset);

    // 4. 字符串交错混合 (Interleave)
    const comps = [comp1, comp2, comp3];
    const max_len = Math.max(...comps.map(c => c.length));

    let interleaved = "";
    for (let k = 0; k < max_len; k++) {
        for (let c of comps) {
            if (k < c.length) {
                interleaved += c[k];
            }
        }
    }

    // 截取前20位作为哈希输入
    const i_str = interleaved.slice(0, 20);

    // 5. 计算 MD5
    const md5_hash = crypto.createHash('md5').update(i_str).digest('hex');

    // 6. 计算前缀 (使用 MD5 前5位映射，字符集切掉后4位)
    const o_prefix = md5_hash.slice(0, 5);
    const hkey_prefix = av(o_prefix, charset, -4);

    // 7. 计算后缀校验和 (使用 MD5 后6位)
    const suffix_part = md5_hash.slice(-6);
    const suffix_input = Array.from(suffix_part).map(c => c.charCodeAt(0));

    // 运行 Km 算法
    const km_output = Km_full(suffix_input);

    // 求和取余
    const checksum_val = km_output.reduce((a, b) => a + b, 0) % 100;
    const checksum_str = String(checksum_val).padStart(2, '0');

    return hkey_prefix + checksum_str;
}

// 生成随机 nonce
function generateNonce() {
    const randomStr = String(Date.now()) + String(Math.random());
    return crypto.createHash('md5').update(randomStr).digest('hex').toUpperCase();
}

// 获取当前时间戳（秒）
function getTimestamp() {
    return Math.floor(Date.now() / 1000);
}

// --- 路由配置 ---
const ROUTES = {
    'emojis_list': {
        path: '/bbs/app/api/emojis/list',
        params: {}
    },
    'data_report': {
        path: '/account/data_report_web/',
        params: {
            type: '104',
            time_: null // 将使用当前时间戳
        }
    },
    'topic_categories': {
        path: '/bbs/app/topic/categories',
        params: {}
    },
    'search_found': {
        path: '/bbs/app/api/search/found',
        params: {
            force_refresh: 'false'
        }
    },
    'search_welcome': {
        path: '/bbs/app/api/search/welcome_page/v2',
        params: {}
    },
    'general_search_v1': {
        path: '/bbs/app/api/general/search/v1',
        params: {
            q: '',
            search_type: 'general',
            is_pull_down: '0',
            dw: '628',
            offset: '0',
            limit: '30',
            no_more: 'false'
        }
    },
    'feeds': {
        path: '/bbs/app/feeds',
        params: {
            pull: '0',
            offset: '0',
            dw: '844'
        }
    },
    'user_profile': {
        path: '/bbs/app/profile/user/profile',
        params: {
            userid: '' // 需要填写用户ID
        }
    },
    'link_tree': {
        path: '/bbs/app/link/tree',
        params: {
            link_id: '' // 需要填写帖子ID
        }
    },
    'comment_list': {
        path: '/bbs/app/api/comment/list',
        params: {
            link_id: '', // 帖子ID
            offset: '0', // 偏移量
            limit: '30' // 每页数量
        }
    },
    'news_list': {
        path: '/bbs/app/link/news',
        params: {
            offset: '0',
            limit: '20'
        }
    },
    'recommend_user': {
        path: '/bbs/app/profile/recommend/user',
        params: {
            offset: '0',
            limit: '20'
        }
    },
    'hot_topics': {
        path: '/bbs/app/api/feed/hot',
        params: {
            offset: '0',
            limit: '20'
        }
    },
    'game_list': {
        path: '/bbs/app/api/game/get_game_list',
        params: {
            offset: '0',
            limit: '30'
        }
    },
    'user_posts': {
        path: '/bbs/app/profile/post/links',
        params: {
            userid: '', // 用户ID
            offset: '0',
            limit: '20'
        }
    },
    'notifications': {
        path: '/account/get_user_notice',
        params: {
            notice_type: '0' // 通知类型：0=全部
        }
    },
    'related_recommend_web': {
        path: '/bbs/app/link/related/recommend_web',
        params: {
            link_id: '',
            h_src: ''
        }
    }
};

// --- URL生成函数 ---
function generateRequestUrl(routeName, customParams = {}, baseOverrides = {}) {
    // 检查路由是否存在
    if (!ROUTES[routeName]) {
        throw new Error(`路由 "${routeName}" 不存在！可用路由: ${Object.keys(ROUTES).join(', ')}`);
    }

    const route = ROUTES[routeName];
    const timestamp = getTimestamp();
    const nonce = generateNonce();

    // 生成 hkey
    const hkey = get_hkey(route.path, timestamp, nonce);

    // 基础参数
    const baseParams = {
        os_type: 'web',
        app: 'heybox',
        client_type: 'web',
        version: '999.0.4',
        web_version: '2.5',
        x_client_type: 'web',
        x_app: 'heybox_website',
        heybox_id: '',
        x_os_type: 'Windows',
        device_info: 'Chrome',
        device_id: '2c2fef8385ccef915e3b3caf94e3aa06'
    };

    // 合并路由参数
    const routeParams = { ...route.params };
    // 处理 time_ 参数
    if (routeParams.time_ === null) {
        routeParams.time_ = timestamp;
    }

    // 合并所有参数
    const allParams = {
        ...routeParams,
        ...baseParams,
        ...baseOverrides,
        ...customParams,
        hkey: hkey,
        _time: timestamp,
        nonce: nonce
    };

    // 构建查询字符串
    const queryString = Object.entries(allParams)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        .join('&');

    // 完整URL
    const fullUrl = `https://api.xiaoheihe.cn${route.path}?${queryString}`;

    return {
        url: fullUrl,
        path: route.path,
        hkey: hkey,
        timestamp: timestamp,
        nonce: nonce
    };
}

// 列出所有可用路由
function listRoutes() {
    console.log('\n可用路由列表:');
    console.log('='.repeat(50));
    Object.entries(ROUTES).forEach(([name, config]) => {
        console.log(`\n路由名称: ${name}`);
        console.log(`路径: ${config.path}`);
        if (Object.keys(config.params).length > 0) {
            console.log(`额外参数: ${JSON.stringify(config.params)}`);
        }
    });
    console.log('\n' + '='.repeat(50));
}

// 导出函数
module.exports = {
    get_hkey,
    generateNonce,
    getTimestamp,
    generateRequestUrl,
    listRoutes,
    ROUTES
};
