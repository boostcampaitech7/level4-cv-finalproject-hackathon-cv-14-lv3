import json

"""
로그에서 action 부분만을 추출하는 함수
"""
log_path = 'test_run_logs_0/trial_0.log'

# 리스트를 나누는 함수
def split_by_reset(log_list):
    result = []
    current_list = []

    for item in log_list:
        if item == "reset":
            if current_list:
                result.append(current_list)
            current_list = [item]  # reset이 있으면 새로운 리스트 시작
        else:
            current_list.append(item)

    # 마지막 리스트가 비어있지 않으면 추가
    if current_list:
        result.append(current_list)

    return result

with open(log_path) as file:
    log_data = file.read()  # 파일 전체 내용 읽기
    lines = log_data.split('\n')
    output_lines = [line.split('>')[1].strip() for line in lines if '>' in line]
    print(output_lines)
# 필터링 조건: reset, search, click만 남기기
filtered_log = [item for item in output_lines if any(keyword in item for keyword in ['reset', 'search', 'click'])]

split_logs = split_by_reset(filtered_log)

log_dict = {
    "output_lines": split_logs
}

# JSON 형식으로 저장
with open('log_data.json', 'w') as json_file:
    json.dump(log_dict, json_file, indent=4)
