/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include <folly/Portability.h>

#if FOLLY_HAS_COROUTINES

#include <folly/experimental/coro/AsyncGenerator.h>
#include <folly/experimental/coro/Task.h>

namespace folly {
namespace python {

template <typename T>
using NextResult = typename coro::AsyncGenerator<T>::NextResult;

template <typename T>
class AsyncGeneratorWrapper {
 public:
  AsyncGeneratorWrapper() = default;
  explicit AsyncGeneratorWrapper(coro::AsyncGenerator<T>&& gen)
      : gen_(std::move(gen)) {}

  coro::Task<NextResult<T>> getNext() {
    co_return co_await gen_.next();
  }

 private:
  coro::AsyncGenerator<T> gen_;
};

} // namespace python
} // namespace folly

#endif
