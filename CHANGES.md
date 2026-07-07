# Registro de Cambios del Proyecto

## Fecha: 2026-07-07

---

## Resumen de Cambios

Se implementó un sistema de control de roles basado en tokens JWT con las siguientes características:

1. **Decorador `require_role`** para proteger endpoints por rol
2. **El token JWT ahora incluye el role del usuario**
3. **Optimización de queries** en el flujo de login (1 query en vez de 2)
4. **El role se almacena en Redis** para eliminar querys al refresh token

---

## Archivos Modificados

---

### 1. `app/dependencies.py`

**Agregado:** Decorador `require_role` para control de acceso por roles.

```python
# role decorator
def require_role(allowed_role: str):
    async def role_checker(token: str = Depends(oauth2_scheme)) -> dict:
        payload = decode_jwt(token)
        user_role = payload.get("role", "user")

        if user_role != allowed_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )

        return payload
    return role_checker
```

**Uso:**
```python
# Solo admins
@router.get("/admin")
async def admin_route(payload: dict = Depends(require_role("admin"))):
    ...

# Solo users
@router.get("/user")
async def user_route(payload: dict = Depends(require_role("user"))):
    ...
```

---

### 2. `app/core/security.py`

**Modificado:** Función `generate_payload` para incluir el role en el token JWT.

**Antes:**
```python
def generate_payload(user_id: uuid.UUID) -> dict:
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid.uuid4())
    }
```

**Después:**
```python
def generate_payload(user_id: uuid.UUID, role: str = "user") -> dict:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid.uuid4())
    }
```

---

### 3. `app/services/auth_service.py`

**Modificado 1:** Import agregado `json`.

```python
import json
```

---

**Modificado 2:** Función `validate_user_data` - Retorna un dict con más información del usuario.

**Antes:**
```python
async def validate_user_data(user_data: UserValidate, db: AsyncSession) -> UUID | None:
    # ... validaciones ...
    return user_in_db.id
```

**Después:**
```python
async def validate_user_data(user_data: UserValidate, db: AsyncSession) -> dict | None:
    # ... validaciones ...
    return {
        "user_id": user_in_db.id,
        "role": user_in_db.role.rolename,
        "is_verified": user_in_db.is_verified
    }
```

---

**Modificado 3:** Función `users_login` - Guarda user_id y role en Redis como JSON.

**Antes:**
```python
await redis_client.setex(f"refresh_token:{str(refresh_token)}", 604800, str(user_data_dict["user_id"]))
```

**Después:**
```python
# Store user_id and role in Redis as JSON
refresh_data = json.dumps({
    "user_id": str(user_data_dict["user_id"]),
    "role": user_data_dict["role"]
})
await redis_client.setex(f"refresh_token:{refresh_token}", 604800, refresh_data)
```

---

**Modificado 4:** Función `generate_access_token` - Lee user_id y role desde Redis (sin query a DB).

**Antes:**
```python
user_id = await redis_client.get(f"refresh_token:{refresh_token}")

# Query a DB para obtener role
result = await db.execute(select(UserTable).filter(UserTable.id == UUID(user_id)))
user = result.scalar_one()
user_role = user.role.rolename
```

**Después:**
```python
stored_data = await redis_client.get(f"refresh_token:{refresh_token}")

# Parse JSON stored in Redis
try:
    refresh_data = json.loads(stored_data)
    user_id = refresh_data["user_id"]
    user_role = refresh_data["role"]
except (json.JSONDecodeError, KeyError, TypeError) as e:
    logger.error(f"Invalid refresh token data format: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )
```

**También guarda el nuevo refresh token como JSON:**
```python
new_refresh_data = json.dumps({
    "user_id": user_id,
    "role": user_role
})
await redis_client.setex(f"refresh_token:{new_refresh_token}", 604800, new_refresh_data)
```

---

## Flujo de Datos

```
Login Flow:
┌─────────────────┐     ┌──────────────────────┐
│ user_data       │────▶│ validate_user_data   │
│ (mail, password)│     │ (1 query a DB)       │
└─────────────────┘     └──────────┬───────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     │ Returns:                   │
                     │ {                          │
                     │   "user_id": UUID,         │
                     │   "role": "user"|"admin",  │
                     │   "is_verified": bool      │
                     │ }                          │
                     └─────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │ generate_payload          │
                    │ (user_id, role)          │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ JWT Token                 │
                    │ {                         │
                    │   "sub": user_id,         │
                    │   "role": "user"|"admin",  │
                    │   "iat", "exp", "jti"     │
                    │ }                         │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Redis                     │
                    │ refresh_token:{token}      │
                    │ {                         │
                    │   "user_id": "...",       │
                    │   "role": "user"          │
                    │ }                         │
                    └──────────────────────────┘
```

```
Refresh Token Flow:
┌─────────────────┐     ┌──────────────────────┐
│ refresh_token   │────▶│ Redis                 │
│                 │     │ get refresh_token    │
└─────────────────┘     └──────────┬───────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     │ Returns JSON:              │
                     │ {                          │
                     │   "user_id": "...",       │
                     │   "role": "user"          │
                     │ }                          │
                     └─────────────┬───────────────┘
                                   │
                                   ▼ (NO QUERY A DB)
                    ┌──────────────────────────┐
                    │ generate_payload          │
                    │ (user_id, role)          │
                    └──────────────────────────┘
```

---

## Beneficios

| Mejora | Descripción |
|--------|-------------|
| **Reducción de queries (Login)** | Login ahora hace 1 query en vez de 2 |
| **Cero queries (Refresh)** | No hace query a DB al refresh token |
| **Escalabilidad** | `validate_user_data` retorna dict, fácil de extender |
| **Control de acceso** | Decorador `require_role` simple de usar |
| **Token completo** | El role está en el token JWT |
| **Redis como cache** | Role almacenado en Redis para acceso rápido |

---

## Manejo de Errores

- **JSON decode error**: Si el formato de Redis es inválido, retorna 500
- **KeyError**: Si falta user_id o role, retorna 500
- **Token reuse detection**: Funciona igual que antes
- **Expired token**: Funciona igual que antes

---

## Notas

- El modelo `UserTable` tiene `role_id` como FK a `RoleTable`
- El modelo usa `lazy="joined"` para cargar el role en la misma query
- El decorador `require_role` extrae el role directamente del token JWT
- Redis almacena JSON `{user_id, role}` para no consultar la DB en refresh
- La solución es más eficiente para proyectos grandes (0 queries en refresh)