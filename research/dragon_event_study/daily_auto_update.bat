@echo off
REM ============================================================
REM 每日自动更新链(收盘后 17:30 由计划任务触发)
REM   1) 数据中台增量(update_all, --no-auto-login: 需 miniQMT 常登录)
REM   2) dragon 回看表尾部(update_tail, 动态认最新交易日 + tushare 定盘门)
REM   3) 重建动态网页(build_dynamic + build_html_dynamic)
REM 任一步失败不中断后续(集合竞价未定盘时 update_tail 自动不写、次日补)。
REM ============================================================
setlocal
set LOG=D:\Code\JQ\战车A\research\dragon_event_study\_auto_update.log
echo. >> "%LOG%"
echo ======== %date% %time% 每日自动更新开始 ======== >> "%LOG%"

REM --- 1) 中台增量 ---
cd /d D:\Code\data_warehouse_app
py -3.10 scripts\update_all.py --no-auto-login >> "%LOG%" 2>&1
echo [%time%] update_all 退出码=%ERRORLEVEL% >> "%LOG%"

REM --- 2) dragon 回看表尾部 ---
cd /d D:\Code\JQ\战车A\research\dragon_event_study
.venv\Scripts\python.exe update_tail.py >> "%LOG%" 2>&1
echo [%time%] update_tail 退出码=%ERRORLEVEL% >> "%LOG%"

REM --- 3) 重建网页 ---
.venv\Scripts\python.exe build_dynamic.py >> "%LOG%" 2>&1
.venv\Scripts\python.exe build_html_dynamic.py >> "%LOG%" 2>&1
echo [%time%] 重建网页 退出码=%ERRORLEVEL% >> "%LOG%"

echo ======== %date% %time% 每日自动更新结束 ======== >> "%LOG%"
endlocal
