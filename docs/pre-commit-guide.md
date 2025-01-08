# Pre-commit Configuration Guide

Pre-commit은 `stage` 상태의 파일들에 대해서 수행되며, `foramtting`을 포함한 다양한 기능을 빠르게 수행해주는, 현업에서 많이 사용하는 도구입니다. 이 문서는 `pre-commit`의 사용법을 설명합니다.

## 🧐 How to use??

```bash
# pre-commit 설치
pip install pre-commit

# 프로젝트에 pre-commit 설정 적용
pre-commit install
```

```bash
# Repository에 있는 모든 파일에 대해 검사 실행
pre-commit run --all-files

# Staged files만 검사
pre-commit run
```

## 📝 설정 파일 (.pre-commit-config.yaml)

```yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-toml
    -   id: debug-statements
    -   id: check-added-large-files
        args: ['--maxkb=1024']

-   repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
    -   id: black
        args: ["--config", "pyproject.toml"]

-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
    -   id: ruff
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
- `check-added-large-files`: 큰 파일의 실수 커밋 방지

### Black - [GitHub](https://github.com/psf/black)

Python 코드 포매터입니다.

- 설정은 `pyproject.toml`을 참조
- 일관된 코드 스타일 강제
- 자동 포매팅 수행

### Ruff : [GitHub](https://github.com/astral-sh/ruff-pre-commit)

빠른 Python 린터입니다.

- `--fix`: 자동으로 수정 가능한 문제 해결
- `--exit-non-zero-on-fix`: 수정 후 상태 보고

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