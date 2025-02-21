## Why should i use Ruff?

- `Ruff`는 전 세계에서 가장 유명한 `python` 코드 품질 관리를 담당하는 도구로, **코드 스타일 검사, 오류 검출** 등을 수행합니다. 아래 `pre-commit`들의 모든 기능을 수행하며, `Rust` 기반이므로 매우 빠르게 작동합니다.

- [Black](https://github.com/psf/black) : `formatting`은 작성된 코드의 줄 간격, 띄어쓰기 등 **양식**을 다듬어 줍니다.
- [isort](https://github.com/PyCQA/isort) : `import`를 활용해서 불러오는 `python library`를 자동으로 **정렬**해줍니다.
- [Flake8](https://github.com/PyCQA/flake8) : 작성한 코드에서 **사용하지 않는** `python library`를 자동으로 제거해줍니다.


## 🧐 How to use??

```bash
# 초기 설정
pip install pre-commit
pre-commit install

# Ruff를 실행합니다.
ruff check --fix .                 # 현재 경로의 모든 파일의 문제를 수정합니다.
ruff check --fix --unsafe-fixes .  # 안전하지 않은 문제도 함께 수정합니다.

ruff format                        # Fix the format

# Run with pre-commit-hooks
pre-commit run --all-files
```

## 📝 설정 파일 (.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: debug-statements
      - id: check-added-large-files
        args: ["--maxkb=1024"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

## Hook 설명

### Pre-commit-hooks

기본적인 파일 검사와 포맷팅을 수행합니다.

- `trailing-whitespace`: 줄 끝의 불필요한 공백 제거
- `end-of-file-fixer`: 파일 끝에 newline 추가
- `check-yaml`: YAML 파일 문법 검사
- `check-toml`: TOML 파일 문법 검사
- `check-json`: JSON 파일 문법 검사
- `debug-statements`: 디버그 구문(pdb, ipdb 등) 검사
- `check-added-large-files`: 큰 파일(ex. checkpoint)의 실수 커밋 방지

### Git Hooks 자동 실행

commit 시 자동으로 실행됩니다:

```bash
git commit -m "메시지"
# pre-commit hooks 자동 실행
```

### Hook 업데이트

```bash
pre-commit autoupdate
```

## 문제 해결

### Hook 건너뛰기

특정 커밋에서 hook을 건너뛰려면:

```bash
git commit -m "메시지" --no-verify
```
